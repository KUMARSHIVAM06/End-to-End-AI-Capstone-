"""
gui/main_gui.py  —  AI Capstone Minimal GUI
=============================================
Tkinter-based interface showing pipeline status and a chat log.

Run:  python gui/main_gui.py [--user Alice] [--simulated] [--no-tts]
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont, scrolledtext, ttk

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.auth     import FaceAuthenticator
from modules.dialog   import DialogEngine
from modules.executor import CommandExecutor
from modules.tts      import Speaker
from modules.stt      import SpeechInput
from utils.logger     import setup_logging

logger = logging.getLogger(__name__)

# ── Colours ──────────────────────────────────────────────────
BG      = "#0f1117"
PANEL   = "#1a1d27"
ACCENT  = "#00e5ff"
GREEN   = "#00e676"
RED     = "#ff1744"
YELLOW  = "#ffd740"
TEXT    = "#e0e0e0"
MUTED   = "#607d8b"
BORDER  = "#263238"


class StatusBar(tk.Frame):
    """Top strip showing pipeline step states."""

    STEPS = ["ENROLL", "AUTH", "DIALOG", "EXEC"]

    def __init__(self, parent):
        super().__init__(parent, bg=PANEL, height=56)
        self._labels: dict[str, tk.Label] = {}
        self._dots:   dict[str, tk.Label] = {}

        for i, step in enumerate(self.STEPS):
            col = tk.Frame(self, bg=PANEL)
            col.pack(side=tk.LEFT, expand=True)

            dot = tk.Label(col, text="●", font=("Courier", 18), fg=MUTED, bg=PANEL)
            dot.pack()
            lbl = tk.Label(col, text=step, font=("Courier", 8), fg=MUTED, bg=PANEL)
            lbl.pack()
            self._labels[step] = lbl
            self._dots[step]   = dot

    def set(self, step: str, state: str):
        """state: idle | active | done | error"""
        color = {
            "idle":   MUTED,
            "active": YELLOW,
            "done":   GREEN,
            "error":  RED,
        }.get(state, MUTED)
        if step in self._labels:
            self._labels[step].config(fg=color)
            self._dots[step].config(fg=color)


class ChatLog(scrolledtext.ScrolledText):
    def __init__(self, parent):
        super().__init__(
            parent,
            bg=BG, fg=TEXT,
            font=("Courier", 11),
            relief=tk.FLAT,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bd=0,
            padx=12, pady=8,
        )
        self.tag_config("system", foreground=ACCENT)
        self.tag_config("user",   foreground=GREEN)
        self.tag_config("error",  foreground=RED)
        self.tag_config("info",   foreground=MUTED)

    def append(self, role: str, text: str):
        self.config(state=tk.NORMAL)
        prefix = {"system": "🤖  ", "user": "👤  ", "error": "⚠️  ", "info": "ℹ️  "}.get(role, "")
        self.insert(tk.END, f"{prefix}{text}\n", role)
        self.see(tk.END)
        self.config(state=tk.DISABLED)


class CapstoneGUI:
    def __init__(self, root: tk.Tk, args):
        self.root = root
        self.args = args
        root.title("AI Capstone System")
        root.configure(bg=BG)
        root.geometry("700x520")
        root.resizable(True, True)

        # ── Modules ──
        self.speaker  = Speaker(enabled=not args.no_tts)
        self.inp      = SpeechInput(use_mic=not args.no_mic)
        self.auth     = FaceAuthenticator(username=args.user, simulated=args.simulated)
        self.dialog   = DialogEngine(username=args.user)
        self.executor = CommandExecutor()

        self._build_ui()
        self._start_pipeline()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=PANEL, height=46)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr, text="⬡  AI CAPSTONE SYSTEM",
            font=("Courier", 13, "bold"), fg=ACCENT, bg=PANEL
        ).pack(side=tk.LEFT, padx=16, pady=10)
        tk.Label(
            hdr, text=f"user: {self.args.user}",
            font=("Courier", 9), fg=MUTED, bg=PANEL
        ).pack(side=tk.RIGHT, padx=16)

        # Status bar
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(fill=tk.X, padx=0, pady=0)

        # Separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # Chat log
        self.chat = ChatLog(self.root)
        self.chat.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        # Input row
        inp_row = tk.Frame(self.root, bg=PANEL)
        inp_row.pack(fill=tk.X, pady=6, padx=8)

        self.entry = tk.Entry(
            inp_row, bg=BORDER, fg=TEXT,
            font=("Courier", 11), relief=tk.FLAT,
            insertbackground=ACCENT,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(4, 6))
        self.entry.bind("<Return>", self._on_submit)

        self.send_btn = tk.Button(
            inp_row, text="SEND",
            bg=ACCENT, fg=BG,
            font=("Courier", 10, "bold"),
            relief=tk.FLAT, padx=12,
            command=self._on_submit,
            state=tk.DISABLED,
        )
        self.send_btn.pack(side=tk.RIGHT, ipady=6)

        self._pending_resolve = None  # callback set by pipeline waiting for input

    # ── Threading helpers ────────────────────────────────────

    def _bg(self, fn, *a, **kw):
        threading.Thread(target=fn, args=a, kwargs=kw, daemon=True).start()

    def _ui(self, fn, *a, **kw):
        self.root.after(0, fn, *a, **kw)

    def _say(self, role: str, text: str):
        self._ui(self.chat.append, role, text)
        self.speaker.say(text)

    # ── User input gate ──────────────────────────────────────

    def _wait_for_input(self) -> str:
        """Block (in background thread) until user submits text."""
        event = threading.Event()
        result: list[str] = []

        def resolve(text: str):
            result.append(text)
            event.set()

        self._pending_resolve = resolve
        self._ui(self._enable_input)
        event.wait()
        self._ui(self._disable_input)
        return result[0] if result else "exit"

    def _enable_input(self):
        self.send_btn.config(state=tk.NORMAL)
        self.entry.config(state=tk.NORMAL)
        self.entry.focus()

    def _disable_input(self):
        self.send_btn.config(state=tk.DISABLED)
        self.entry.config(state=tk.DISABLED)

    def _on_submit(self, *_):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self._ui(self.chat.append, "user", text)
        if self._pending_resolve:
            cb = self._pending_resolve
            self._pending_resolve = None
            cb(text)

    # ── Pipeline ─────────────────────────────────────────────

    def _start_pipeline(self):
        self._bg(self._run_pipeline)

    def _run_pipeline(self):
        # Step 1 – Enroll
        self._ui(self.status_bar.set, "ENROLL", "active")
        if not self.auth.is_enrolled():
            self._say("system", "No face enrolled. Enrolling now…")
            ok = self.auth.enroll(display=False)
            if not ok:
                self._say("error", "Enrollment failed.")
                self._ui(self.status_bar.set, "ENROLL", "error")
                return
        self._say("info", "Face profile ready.")
        self._ui(self.status_bar.set, "ENROLL", "done")

        # Step 2 – Auth
        self._ui(self.status_bar.set, "AUTH", "active")
        self._say("system", self.dialog.auth_prompt())

        authenticated = False
        while True:
            result = self.auth.authenticate(timeout=10, display=False)
            if result:
                self._say("system", self.dialog.auth_success())
                self._ui(self.status_bar.set, "AUTH", "done")
                authenticated = True
                break
            else:
                fail_msg, blocked = self.dialog.auth_failure()
                self._say("error", fail_msg)
                if blocked:
                    self._ui(self.status_bar.set, "AUTH", "error")
                    return

        # Step 3 – Dialog loop
        self._ui(self.status_bar.set, "DIALOG", "active")
        while True:
            self._say("system", self.dialog.prompt_command())
            user_text = self._wait_for_input()

            intent, dialog_response = self.dialog.process(user_text)
            self._say("system", dialog_response)

            if intent == "exit":
                self._ui(self.status_bar.set, "DIALOG", "done")
                break

            if intent in ("help", "greet", "unknown", "cancel", "re-confirm"):
                continue

            # Confirm → execute
            if intent == "confirm":
                self._ui(self.status_bar.set, "EXEC", "active")
                last_cmd = self.dialog.ctx.last_command
                ex_result = self.executor.execute(last_cmd)
                self._say("system" if ex_result.success else "error", ex_result.output)
                self._ui(
                    self.status_bar.set, "EXEC",
                    "done" if ex_result.success else "error"
                )
                # Reset EXEC dot for next command
                self.root.after(1500, lambda: self._ui(self.status_bar.set, "EXEC", "idle"))
                from modules.dialog import DialogState
                self.dialog.ctx.state = DialogState.READY


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--user",      default="User")
    p.add_argument("--simulated", action="store_true")
    p.add_argument("--no-tts",    action="store_true")
    p.add_argument("--no-mic",    action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    setup_logging("INFO")
    args = parse_args()
    root = tk.Tk()
    app  = CapstoneGUI(root, args)
    root.mainloop()
