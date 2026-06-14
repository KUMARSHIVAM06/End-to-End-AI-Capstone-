"""
modules/dialog.py  —  Rule-Based Dialog Engine
================================================
Manages conversation state, greets the user, prompts for commands,
confirms actions, and handles errors.  Completely independent of I/O
(caller supplies / receives strings).

Designed so interns can slot in NLP (spaCy, transformers) without
changing the interface.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable

logger = logging.getLogger(__name__)


# ── Conversation State Machine ───────────────────────────────

class DialogState(Enum):
    IDLE        = auto()
    GREETING    = auto()
    AUTH_PROMPT = auto()
    AUTH_FAILED = auto()
    READY       = auto()
    AWAITING    = auto()
    CONFIRMING  = auto()
    EXECUTING   = auto()
    DONE        = auto()
    ERROR       = auto()


@dataclass
class DialogContext:
    state:           DialogState  = DialogState.IDLE
    username:        str          = "User"
    last_command:    str          = ""
    turn_count:      int          = 0
    failed_attempts: int          = 0
    history:         list[dict]   = field(default_factory=list)

    def record(self, role: str, text: str):
        self.history.append({"role": role, "text": text})
        self.turn_count += 1


# ── Intent Patterns ──────────────────────────────────────────

INTENTS = {
    "exit":      r"\b(exit|quit|bye|goodbye|stop|shut\s*down)\b",
    "help":      r"\b(help|commands|what can you do|options)\b",
    "confirm":   r"^(yes|yeah|yep|sure|ok|okay|confirm|do it|proceed|go ahead)\.?$",
    "cancel":    r"^(no|nope|cancel|abort|never mind|stop)\.?$",
    "time":      r"\b(time|clock)\b",
    "date":      r"\b(date|day|today)\b",
    "search":    r"\b(search|google|find|look up)\b",
    "open":      r"\b(open|launch|start|run)\b",
    "calculate": r"\b(calc|calculate|compute|math|how much|what is)\b",
    "joke":      r"\b(joke|funny|laugh|humor)\b",
    "greet":     r"^(hi|hello|hey|good\s*(morning|afternoon|evening))\b",
}

TEMPLATES = {
    "welcome":     [
        "Welcome back, {name}! Authentication successful. What would you like to do?",
        "Hello, {name}. I've verified your identity. How can I assist you today?",
        "Good to see you, {name}. You're authenticated. Ready for your command.",
    ],
    "auth_prompt": [
        "Please look at the camera to verify your identity.",
        "Face authentication required. Please face the camera.",
        "Starting face scan. Please hold still and look at the camera.",
    ],
    "auth_fail":   [
        "Face authentication failed. Please try again.",
        "I couldn't verify your identity. Retrying…",
        "Authentication unsuccessful. Let's try once more.",
    ],
    "auth_blocked":[
        "Too many failed attempts. Access denied for security.",
    ],
    "prompt":      [
        "What would you like me to do?",
        "I'm listening. Go ahead.",
        "Your command?",
    ],
    "confirm":     [
        "You want me to: \"{cmd}\". Shall I proceed? (yes/no)",
        "Got it — \"{cmd}\". Should I go ahead? (yes/no)",
        "I'll \"{cmd}\". Confirm? (yes/no)",
    ],
    "cancel":      [
        "Okay, cancelled. What else can I do?",
        "No problem. Anything else?",
        "Command cancelled.",
    ],
    "unknown":     [
        "I didn't understand that. Say 'help' for a list of commands.",
        "Not sure what you mean. Try 'help' to see what I can do.",
        "Could you rephrase that? Or say 'help'.",
    ],
    "goodbye":     [
        "Goodbye, {name}! Session ended.",
        "See you next time, {name}. Take care!",
        "Logging you out. Goodbye!",
    ],
    "help":        [
        (
            "Available commands:\n"
            "  • tell me the time / date\n"
            "  • search for <query>\n"
            "  • open <app name>\n"
            "  • calculate <expression>\n"
            "  • tell me a joke\n"
            "  • exit / quit"
        )
    ],
    "error":       [
        "Something went wrong. Let's try again.",
        "An error occurred. Please repeat your command.",
    ],
}


def _pick(key: str, **kwargs) -> str:
    templates = TEMPLATES.get(key, ["…"])
    text = random.choice(templates)
    return text.format(**kwargs) if kwargs else text


class DialogEngine:
    """
    Stateful rule-based dialog manager.

    Usage::

        dlg = DialogEngine(username="Alice")
        print(dlg.greet())                    # starts session
        print(dlg.auth_prompt())
        # … run face auth …
        print(dlg.auth_success())
        text = input("Command: ")
        intent, response = dlg.process(text)
    """

    MAX_AUTH_ATTEMPTS = 3

    def __init__(self, username: str = "User"):
        self.ctx = DialogContext(username=username)

    # ── State transitions ─────────────────────────────────────

    def greet(self) -> str:
        self.ctx.state = DialogState.GREETING
        msg = f"AI Capstone System — Hello!"
        self.ctx.record("system", msg)
        return msg

    def auth_prompt(self) -> str:
        self.ctx.state = DialogState.AUTH_PROMPT
        msg = _pick("auth_prompt")
        self.ctx.record("system", msg)
        return msg

    def auth_success(self) -> str:
        self.ctx.state = DialogState.READY
        self.ctx.failed_attempts = 0
        msg = _pick("welcome", name=self.ctx.username)
        self.ctx.record("system", msg)
        return msg

    def auth_failure(self) -> tuple[str, bool]:
        """Returns (message, is_blocked)."""
        self.ctx.failed_attempts += 1
        blocked = self.ctx.failed_attempts >= self.MAX_AUTH_ATTEMPTS
        if blocked:
            self.ctx.state = DialogState.AUTH_FAILED
            msg = _pick("auth_blocked")
        else:
            msg = _pick("auth_fail")
        self.ctx.record("system", msg)
        return msg, blocked

    def prompt_command(self) -> str:
        self.ctx.state = DialogState.AWAITING
        msg = _pick("prompt")
        self.ctx.record("system", msg)
        return msg

    def farewell(self) -> str:
        self.ctx.state = DialogState.DONE
        msg = _pick("goodbye", name=self.ctx.username)
        self.ctx.record("system", msg)
        return msg

    def error(self) -> str:
        self.ctx.state = DialogState.ERROR
        msg = _pick("error")
        self.ctx.record("system", msg)
        return msg

    # ── Main processing ───────────────────────────────────────

    def process(self, user_input: str) -> tuple[str, str]:
        """
        Parse user input and return (intent, response_text).

        Handles confirmation flow internally.
        """
        text = user_input.strip().lower()
        self.ctx.record("user", user_input)

        # ── Confirmation branch ──
        if self.ctx.state == DialogState.CONFIRMING:
            if re.search(INTENTS["confirm"], text):
                self.ctx.state = DialogState.EXECUTING
                response = f"Executing: {self.ctx.last_command}"
                self.ctx.record("system", response)
                return "confirm", response
            elif re.search(INTENTS["cancel"], text):
                self.ctx.state = DialogState.READY
                response = _pick("cancel")
                self.ctx.record("system", response)
                return "cancel", response
            else:
                response = f"Please answer yes or no. Execute \"{self.ctx.last_command}\"?"
                self.ctx.record("system", response)
                return "re-confirm", response

        # ── Intent matching ──
        intent = self._classify(text)
        logger.debug(f"[Dialog] intent='{intent}' for input='{text[:60]}'")

        if intent == "exit":
            return "exit", self.farewell()

        if intent == "help":
            response = _pick("help")
            self.ctx.record("system", response)
            return "help", response

        if intent == "greet":
            response = f"Hello! I'm ready. {_pick('prompt')}"
            self.ctx.record("system", response)
            return "greet", response

        if intent in ("time", "date", "search", "open", "calculate", "joke"):
            # Ask for confirmation before acting
            self.ctx.last_command = user_input.strip()
            self.ctx.state = DialogState.CONFIRMING
            response = _pick("confirm", cmd=self.ctx.last_command)
            self.ctx.record("system", response)
            return intent, response

        # Unknown
        response = _pick("unknown")
        self.ctx.record("system", response)
        return "unknown", response

    def _classify(self, text: str) -> str:
        for intent, pattern in INTENTS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return intent
        return "unknown"

    def get_history(self) -> list[dict]:
        return self.ctx.history.copy()

    def reset(self):
        self.ctx = DialogContext(username=self.ctx.username)
