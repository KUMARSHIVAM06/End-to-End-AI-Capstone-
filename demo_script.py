"""
demo/demo_script.py  —  Interactive Demo (No Camera / No Mic)
=============================================================
Runs through the full pipeline with scripted inputs so anyone
can reproduce the demo on any machine without hardware.

Usage:
  python demo/demo_script.py
  python demo/demo_script.py --slow     # add pauses for presentation
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.auth     import FaceAuthenticator
from modules.dialog   import DialogEngine, DialogState
from modules.executor import CommandExecutor
from modules.tts      import Speaker

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
MUTED  = "\033[90m"


def section(title: str):
    print(f"\n{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{CYAN}{'─'*60}{RESET}")


def bot(text: str, speaker: Speaker):
    print(f"{GREEN}🤖  {text}{RESET}")
    speaker.say(text)


def user(text: str, delay: float = 0):
    if delay:
        time.sleep(delay)
    print(f"{YELLOW}👤  {text}{RESET}")


def info(text: str):
    print(f"{MUTED}    ℹ  {text}{RESET}")


DEMO_SCRIPT = [
    # (user_says, description)
    ("what time is it",     "Ask for the current time"),
    ("yes",                  "Confirm the command"),
    ("tell me a joke",       "Ask for a joke"),
    ("yes",                  "Confirm"),
    ("search for Python AI", "Web search command"),
    ("yes",                  "Confirm"),
    ("calculate 12 * 8",     "Math calculation"),
    ("yes",                  "Confirm"),
    ("help",                 "List available commands"),
    ("exit",                 "End the session"),
]


def run(slow: bool = False, no_tts: bool = True):
    speaker = Speaker(enabled=not no_tts)
    pause   = 1.2 if slow else 0.0

    print(f"\n{BOLD}{'═'*60}")
    print("  🤖  AI CAPSTONE — DEMO SCRIPT")
    print(f"{'═'*60}{RESET}\n")
    print(f"  Mode     : {'SLOW (presentation)' if slow else 'FAST'}")
    print(f"  TTS      : {'ON' if not no_tts else 'OFF (text-only)'}")
    print(f"  Camera   : SIMULATED")
    print(f"  Mic      : SCRIPTED\n")

    # ── Step 1: Enroll ──────────────────────────────────────
    section("STEP 1 / 3  —  Face Enrollment (Simulated)")
    auth = FaceAuthenticator(simulated=True, username="DemoUser")
    info("Simulating camera enrollment…")
    time.sleep(0.4)
    ok = auth.enroll()
    assert ok, "Enroll failed"
    bot("Face enrolled successfully!", speaker)
    time.sleep(pause)

    # ── Step 2: Authenticate ────────────────────────────────
    section("STEP 2 / 3  —  Face Authentication (Simulated)")
    dialog = DialogEngine(username="DemoUser")
    bot(dialog.auth_prompt(), speaker)
    info("Simulating face scan…")
    time.sleep(0.6)
    result = auth.authenticate()
    assert result, "Auth failed"
    bot(dialog.auth_success(), speaker)
    time.sleep(pause)

    # ── Step 3: Dialog + Execution ──────────────────────────
    section("STEP 3 / 3  —  Dialog & Command Execution")
    executor = CommandExecutor()

    for cmd, description in DEMO_SCRIPT:
        time.sleep(pause * 0.5)
        info(f"Demo input: {description}")
        bot(dialog.prompt_command(), speaker)
        user(cmd, delay=0.3)

        intent, dialog_response = dialog.process(cmd)
        bot(dialog_response, speaker)
        time.sleep(pause * 0.3)

        if intent == "exit":
            break

        if intent in ("help", "greet", "unknown", "cancel"):
            continue

        if intent == "confirm":
            ex_result = executor.execute(dialog.ctx.last_command)
            status = GREEN if ex_result.success else RED
            print(f"{status}    → {ex_result.output}{RESET}")
            dialog.ctx.state = DialogState.READY

    # ── Summary ─────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*60}")
    print("  ✅  Demo complete!")
    print(f"  Session turns : {dialog.ctx.turn_count}")
    print(f"{'═'*60}{RESET}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--slow",   action="store_true", help="Add pauses for live presentation")
    p.add_argument("--tts",    action="store_true", help="Enable TTS audio")
    args = p.parse_args()
    run(slow=args.slow, no_tts=not args.tts)
