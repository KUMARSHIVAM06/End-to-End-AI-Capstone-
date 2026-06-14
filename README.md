# 🤖 End-to-End AI Capstone System

A modular AI pipeline that combines **face authentication**, a **rule-based dialog engine**, and a **command executor** into one cohesive application — available as both a CLI and a minimal Tkinter GUI.

Built for interns to learn modular design and to reuse components across projects.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Capstone Pipeline                  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   modules/   │  │   modules/   │  │   modules/   │  │
│  │   auth.py    │→ │   dialog.py  │→ │  executor.py │  │
│  │              │  │              │  │              │  │
│  │ FaceAuth     │  │ DialogEngine │  │ CommandExec  │  │
│  │ (OpenCV)     │  │ (Rule-based) │  │ (OS/Browser) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ↑                 ↑                 ↑           │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │   modules/   │  │   modules/   │                    │
│  │    stt.py    │  │    tts.py    │                    │
│  │ (Speech In)  │  │ (Speech Out) │                    │
│  └──────────────┘  └──────────────┘                    │
│                                                         │
│         CLI: cli/main_cli.py                            │
│         GUI: gui/main_gui.py                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai_capstone/
│
├── modules/                    # ← Reusable module library
│   ├── __init__.py
│   ├── auth.py                 # Face detection & authentication
│   ├── dialog.py               # Rule-based dialog state machine
│   ├── executor.py             # Command → OS/browser action router
│   ├── tts.py                  # Text-to-speech wrapper
│   └── stt.py                  # Speech-to-text / keyboard wrapper
│
├── cli/
│   └── main_cli.py             # CLI entry point
│
├── gui/
│   └── main_gui.py             # Tkinter GUI entry point
│
├── demo/
│   └── demo_script.py          # Scripted demo (no hardware required)
│
├── tests/
│   └── test_capstone.py        # pytest unit + integration tests
│
├── utils/
│   └── logger.py               # Shared logging setup
│
├── data/faces/                 # Enrolled face images (auto-created)
├── logs/                       # Runtime logs (auto-created)
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### Prerequisites
- Python 3.10+
- Webcam (optional — simulated mode available)
- Microphone (optional — keyboard mode available)

### Install
```bash
pip install -r requirements.txt
```

---

## ▶️ Running

### Demo (no hardware — best for first run)
```bash
python demo/demo_script.py
python demo/demo_script.py --slow    # add pauses for presentations
python demo/demo_script.py --tts     # enable audio
```

### CLI — full voice pipeline
```bash
python cli/main_cli.py
python cli/main_cli.py --user Alice
python cli/main_cli.py --simulated --no-mic   # no camera, keyboard input
python cli/main_cli.py --enroll               # re-enroll face first
```

### GUI — Tkinter interface
```bash
python gui/main_gui.py
python gui/main_gui.py --simulated --no-tts
```

### Tests
```bash
python -m pytest tests/ -v
python -m pytest tests/ -v -k "integration"   # integration only
```

---

## 🔌 CLI Flags

| Flag | Description |
|---|---|
| `--user NAME` | Set username for the session |
| `--simulated` | Skip real camera (uses placeholder) |
| `--no-mic` | Use keyboard instead of microphone |
| `--no-tts` | Disable audio (text output only) |
| `--enroll` | Force face enrollment before session |
| `--log-level` | DEBUG / INFO / WARNING |

---

## 🧩 Module Reference

### `FaceAuthenticator` (`modules/auth.py`)
```python
auth = FaceAuthenticator(username="Alice", simulated=True)
auth.enroll()          # capture reference face
auth.authenticate()    # verify face → True/False
auth.is_enrolled()     # check enroll state
```

### `DialogEngine` (`modules/dialog.py`)
```python
dlg = DialogEngine(username="Alice")
dlg.auth_prompt()          # → "Please look at the camera"
dlg.auth_success()         # → "Welcome back, Alice!"
intent, resp = dlg.process("what time is it")
# intent → "time",  resp → confirmation prompt
dlg.get_history()          # → [{role, text}, …]
```

### `CommandExecutor` (`modules/executor.py`)
```python
ex = CommandExecutor()
result = ex.execute("calculate 6 * 7")
# ExecutionResult(success=True, output="Result of '6 * 7' = 42")
```

### `Speaker` (`modules/tts.py`)
```python
speaker = Speaker(enabled=True)
speaker.say("Hello!")   # speaks + prints
```

### `SpeechInput` (`modules/stt.py`)
```python
inp = SpeechInput(use_mic=True)
text = inp.get_input()   # mic or keyboard, returns str | None
```

---

## 💬 Supported Commands

| Category | Phrases |
|---|---|
| Time | "what time is it", "tell me the time" |
| Date | "what's today's date", "what day is it" |
| Search | "search for python", "google AI trends" |
| Open App | "open notepad", "open calculator", "open terminal" |
| Website | "open youtube", "open github" |
| Math | "calculate 25 * 4", "what is 100 / 8" |
| Joke | "tell me a joke", "make me laugh" |
| Help | "help", "what can you do" |
| Exit | "exit", "quit", "bye" |

---

## 🔁 Intern Reuse Guide

Each module is self-contained and independently importable:

```python
# Use just the dialog engine in another project
from modules.dialog import DialogEngine

# Use just the executor
from modules.executor import CommandExecutor

# Use just face auth
from modules.auth import FaceAuthenticator
```

All modules follow the same pattern:
- Constructor accepts config (simulated, paths, flags)
- Methods return typed results or primitives
- Errors are logged and never crash the caller

---

## 🛡️ Error Handling

| Scenario | Behaviour |
|---|---|
| No camera | Simulated mode auto-activates |
| No microphone | Falls back to keyboard input |
| pyttsx3 unavailable | Falls back to print-only |
| Auth fails 3× | Session blocked, informative message |
| Unknown command | Dialog asks user to try 'help' |
| Executor error | Returns `ExecutionResult(success=False, …)` |

All events are logged to `logs/capstone.log`.

---

## 📄 License
MIT — free to use, modify, and build upon.
