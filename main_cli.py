"""
cli/main_cli.py  —  End-to-End AI Capstone  (CLI Entry Point)
==============================================================
Pipeline:
  1. Face Authentication  (modules/auth.py)
  2. Rule-Based Dialog    (modules/dialog.py)
  3. Command Execution    (modules/executor.py)

Run:
  python cli/main_cli.py
  python cli/main_cli.py --user Alice --no-mic --simulated
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# ── Allow running from repo root ────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.auth     import FaceAuthenticator
from modules.dialog   import DialogEngine
from modules.executor import CommandExecutor
from modules.tts      import Speaker
from modules.stt      import SpeechInput
from utils.logger     import setup_logging

# ── Banner ───────────────────────────────────────────────────
BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      🤖  End-to-End AI Capstone System  v1.0               ║
║                                                              ║
║   [ Face Auth ]  →  [ Dialog ]  →  [ Command Executor ]    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Capstone — Face Auth + Dialog + Command Executor"
    )
    parser.add_argument("--user",       default="User",   help="Username for session")
    parser.add_argument("--no-mic",     action="store_true", help="Use keyboard instead of mic")
    parser.add_argument("--no-tts",     action="store_true", help="Disable text-to-speech audio")
    parser.add_argument("--simulated",  action="store_true", help="Simulated face auth (no camera)")
    parser.add_argument("--enroll",     action="store_true", help="Enroll face before starting")
    parser.add_argument("--log-level",  default="INFO",   choices=["DEBUG", "INFO", "WARNING"])
    return parser.parse_args()


def print_step(step: int, total: int, label: str):
    bar = "█" * step + "░" * (total - step)
    print(f"\n  Step {step}/{total}  [{bar}]  {label}")


def run(args):
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    print(BANNER)

    # ── Initialise modules ───────────────────────────────────
    speaker  = Speaker(enabled=not args.no_tts)
    inp      = SpeechInput(use_mic=not args.no_mic)
    auth     = FaceAuthenticator(username=args.user, simulated=args.simulated)
    dialog   = DialogEngine(username=args.user)
    executor = CommandExecutor()

    # ── Step 1: Enroll (optional) ────────────────────────────
    print_step(1, 3, "Face Enrollment / Check")
    if args.enroll or not auth.is_enrolled():
        speaker.say("Starting face enrollment. Please look at the camera.")
        ok = auth.enroll(display=not args.simulated)
        if not ok:
            speaker.say("Enrollment failed. Exiting.")
            return
        speaker.say("Enrollment complete!")

    # ── Step 2: Authenticate ─────────────────────────────────
    print_step(2, 3, "Face Authentication")
    msg = dialog.auth_prompt()
    speaker.say(msg)

    authenticated = False
    while True:
        result = auth.authenticate(timeout=10.0, display=not args.simulated)
        if result:
            speaker.say(dialog.auth_success())
            authenticated = True
            break
        else:
            fail_msg, blocked = dialog.auth_failure()
            speaker.say(fail_msg)
            if blocked:
                logger.warning("Authentication blocked – too many failures.")
                return

    if not authenticated:
        return

    # ── Step 3: Dialog + Command Loop ───────────────────────
    print_step(3, 3, "Command Session")
    time.sleep(0.3)

    while True:
        try:
            prompt_msg = dialog.prompt_command()
            speaker.say(prompt_msg)

            user_text = inp.get_input()
            if user_text is None:
                speaker.say("I didn't catch that. Please try again.")
                continue

            print(f"  👤  {user_text}")
            intent, dialog_response = dialog.process(user_text)
            speaker.say(dialog_response)

            if intent == "exit":
                break

            if intent in ("help", "greet", "unknown", "cancel", "re-confirm"):
                continue

            # Confirmation received → execute
            if intent == "confirm":
                last_cmd = dialog.ctx.last_command
                result = executor.execute(last_cmd)
                speaker.say(result.output)
                dialog.ctx.state = __import__(
                    "modules.dialog", fromlist=["DialogState"]
                ).DialogState.READY
                continue

            # Intent matched (time / date / joke / …) → confirm step handled by dialog
            # Nothing else to do here; next iteration will ask for confirmation answer

        except KeyboardInterrupt:
            speaker.say(dialog.farewell())
            break
        except Exception as exc:
            logger.error(f"Main loop error: {exc}", exc_info=True)
            speaker.say(dialog.error())

    # ── Session summary ──────────────────────────────────────
    print("\n" + "─" * 60)
    print(f"  Session turns : {dialog.ctx.turn_count}")
    print(f"  Commands run  : {sum(1 for h in dialog.get_history() if h['role'] == 'user')}")
    print("─" * 60 + "\n")


if __name__ == "__main__":
    run(parse_args())
