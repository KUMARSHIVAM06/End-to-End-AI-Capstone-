"""
modules/executor.py  —  Command Executor
=========================================
Maps high-level intents to OS/browser actions.
Thin wrapper so business logic (dialog) stays separate from side effects.

Reuses the same COMMAND_MAP pattern from Project-1's voice_assistant.py.
"""

from __future__ import annotations

import datetime
import logging
import math
import os
import platform
import random
import re
import subprocess
import webbrowser
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM = platform.system()

# ── Result container ─────────────────────────────────────────

@dataclass
class ExecutionResult:
    success: bool
    intent:  str
    command: str
    output:  str
    data:    Any = None

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.output}"


# ── Sub-handlers ─────────────────────────────────────────────

JOKES = [
    "Why do programmers prefer dark mode? Light attracts bugs!",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar and asks two tables: 'Can I JOIN you?'",
    "I told my AI assistant a joke. It said it didn't have a sense of humor. I said, 'Well, you're getting there.'",
    "Debugging: being the detective in a crime movie where you are also the murderer.",
]

APP_MAP: dict[str, dict[str, str]] = {
    "notepad":      {"Windows": "notepad",            "Darwin": "open -a TextEdit",     "Linux": "gedit"},
    "calculator":   {"Windows": "calc",               "Darwin": "open -a Calculator",   "Linux": "gnome-calculator"},
    "browser":      {"Windows": "start chrome",       "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
    "chrome":       {"Windows": "start chrome",       "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
    "firefox":      {"Windows": "start firefox",      "Darwin": "open -a Firefox",      "Linux": "firefox"},
    "terminal":     {"Windows": "start cmd",          "Darwin": "open -a Terminal",     "Linux": "gnome-terminal"},
    "file manager": {"Windows": "explorer",           "Darwin": "open .",               "Linux": "nautilus"},
    "paint":        {"Windows": "mspaint",            "Darwin": "open -a Paintbrush",   "Linux": "gimp"},
    "music":        {"Windows": "start wmplayer",     "Darwin": "open -a Music",        "Linux": "rhythmbox"},
    "camera":       {"Windows": "start microsoft.windows.camera:", "Darwin": "open -a 'Photo Booth'", "Linux": "cheese"},
    "word":         {"Windows": "start winword",      "Darwin": "open -a 'Microsoft Word'", "Linux": "libreoffice --writer"},
    "excel":        {"Windows": "start excel",        "Darwin": "open -a 'Microsoft Excel'", "Linux": "libreoffice --calc"},
}

SITE_MAP = {
    "youtube":   "https://youtube.com",
    "google":    "https://google.com",
    "github":    "https://github.com",
    "wikipedia": "https://wikipedia.org",
    "gmail":     "https://mail.google.com",
    "twitter":   "https://twitter.com",
    "linkedin":  "https://linkedin.com",
}


def _run_app(name: str) -> ExecutionResult:
    key = next((k for k in APP_MAP if k in name.lower()), None)
    if key is None:
        return ExecutionResult(False, "open", name, f"Unknown application: '{name}'")
    cmd = APP_MAP[key].get(SYSTEM)
    if not cmd:
        return ExecutionResult(False, "open", name, f"'{key}' not supported on {SYSTEM}")
    try:
        subprocess.Popen(cmd, shell=True)
        return ExecutionResult(True, "open", name, f"Opened {key}.")
    except Exception as exc:
        return ExecutionResult(False, "open", name, f"Failed to open {key}: {exc}")


def _web_search(query: str) -> ExecutionResult:
    clean = re.sub(r".*(search\s*(for)?|google|find|look\s*up)\s*", "", query, flags=re.IGNORECASE).strip()
    if not clean:
        clean = query
    url = f"https://www.google.com/search?q={clean.replace(' ', '+')}"
    webbrowser.open(url)
    return ExecutionResult(True, "search", query, f"Searching Google for: '{clean}'", data=url)


def _open_site(query: str) -> ExecutionResult:
    for keyword, url in SITE_MAP.items():
        if keyword in query.lower():
            webbrowser.open(url)
            return ExecutionResult(True, "open", query, f"Opened {url}")
    return _web_search(query)


def _get_time() -> ExecutionResult:
    now = datetime.datetime.now()
    msg = f"Current time: {now.strftime('%I:%M %p')}"
    return ExecutionResult(True, "time", "time", msg, data=now)


def _get_date() -> ExecutionResult:
    now = datetime.datetime.now()
    msg = f"Today is {now.strftime('%A, %B %d, %Y')}"
    return ExecutionResult(True, "date", "date", msg, data=now)


def _calculate(expression: str) -> ExecutionResult:
    raw = re.sub(r".*(calc(ulate)?|compute|math|how\s*much\s*is|what\s*is)\s*", "", expression, flags=re.IGNORECASE).strip()
    safe = re.sub(r"[^0-9+\-*/().^\s]", "", raw)
    try:
        result = eval(safe, {"__builtins__": {}}, {"sqrt": math.sqrt, "pi": math.pi, "abs": abs})
        msg = f"Result of '{safe}' = {result}"
        return ExecutionResult(True, "calculate", expression, msg, data=result)
    except Exception as exc:
        return ExecutionResult(False, "calculate", expression, f"Could not calculate '{raw}': {exc}")


def _joke() -> ExecutionResult:
    j = random.choice(JOKES)
    return ExecutionResult(True, "joke", "joke", j)


# ── Routing table ─────────────────────────────────────────────

_ROUTES: list[tuple[tuple[str, ...], callable]] = [
    (("time", "clock"),                   lambda cmd: _get_time()),
    (("date", "day", "today"),            lambda cmd: _get_date()),
    (("joke", "funny", "laugh"),          lambda cmd: _joke()),
    (("calculate", "compute", "how much", "what is"), lambda cmd: _calculate(cmd)),
    (("search", "google", "find", "look up"),         lambda cmd: _web_search(cmd)),
    (("youtube", "github", "wikipedia", "gmail", "twitter", "linkedin"), lambda cmd: _open_site(cmd)),
    (("open", "launch", "start"),         lambda cmd: _run_app(re.sub(r"\b(open|launch|start)\b", "", cmd).strip())),
]


class CommandExecutor:
    """
    Routes a command string (or intent) to the correct handler.

    Usage::

        ex = CommandExecutor()
        result = ex.execute("search for python tutorials")
        print(result)
    """

    def execute(self, command: str, intent: str | None = None) -> ExecutionResult:
        cmd_lower = command.lower().strip()
        logger.info(f"[Executor] Executing: '{command}' (hint: {intent})")

        for keywords, handler in _ROUTES:
            if any(kw in cmd_lower for kw in keywords):
                try:
                    result = handler(command)
                    logger.info(f"[Executor] Result: {result}")
                    return result
                except Exception as exc:
                    logger.error(f"[Executor] Handler error: {exc}", exc_info=True)
                    return ExecutionResult(False, intent or "unknown", command, f"Execution error: {exc}")

        return ExecutionResult(
            False, "unknown", command,
            f"No handler found for: '{command}'. Say 'help' for options."
        )

    def execute_by_intent(self, intent: str, original_command: str) -> ExecutionResult:
        """Shortcut when intent is already known from the dialog engine."""
        intent_to_keywords = {
            "time":      "time",
            "date":      "date",
            "joke":      "joke",
            "calculate": "calculate",
            "search":    "search",
            "open":      "open",
        }
        mapped = intent_to_keywords.get(intent, "")
        if mapped and mapped not in original_command.lower():
            return self.execute(f"{mapped} {original_command}")
        return self.execute(original_command, intent)
