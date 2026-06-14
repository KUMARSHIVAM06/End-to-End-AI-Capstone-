"""
tests/test_capstone.py  —  Unit + Integration Tests
=====================================================
Run:  python -m pytest tests/ -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from modules.dialog   import DialogEngine, DialogState
from modules.executor import CommandExecutor
from modules.auth     import FaceAuthenticator


# ══════════════════════════════════════════════
#  FaceAuthenticator (simulated)
# ══════════════════════════════════════════════

class TestFaceAuth:
    def setup_method(self):
        self.auth = FaceAuthenticator(simulated=True, username="test_user")

    def test_enroll_simulated(self):
        assert self.auth.enroll() is True

    def test_authenticate_simulated(self):
        assert self.auth.authenticate() is True

    def test_is_enrolled_after_enroll(self, tmp_path):
        auth = FaceAuthenticator(simulated=True, data_dir=tmp_path)
        auth.enroll()
        assert auth.is_enrolled()


# ══════════════════════════════════════════════
#  DialogEngine
# ══════════════════════════════════════════════

class TestDialogEngine:
    def setup_method(self):
        self.dlg = DialogEngine(username="TestUser")

    def test_greet_returns_string(self):
        msg = self.dlg.greet()
        assert isinstance(msg, str) and len(msg) > 0

    def test_auth_prompt(self):
        msg = self.dlg.auth_prompt()
        assert "camera" in msg.lower() or "face" in msg.lower()

    def test_auth_success_changes_state(self):
        self.dlg.auth_success()
        assert self.dlg.ctx.state == DialogState.READY

    def test_auth_failure_increments(self):
        self.dlg.auth_failure()
        assert self.dlg.ctx.failed_attempts == 1

    def test_auth_blocked_after_max_attempts(self):
        for _ in range(DialogEngine.MAX_AUTH_ATTEMPTS):
            msg, blocked = self.dlg.auth_failure()
        assert blocked

    def test_process_exit(self):
        self.dlg.auth_success()
        intent, _ = self.dlg.process("exit")
        assert intent == "exit"

    def test_process_help(self):
        self.dlg.auth_success()
        intent, response = self.dlg.process("help")
        assert intent == "help"
        assert "commands" in response.lower() or "available" in response.lower()

    def test_process_time_triggers_confirm(self):
        self.dlg.auth_success()
        intent, response = self.dlg.process("what time is it")
        assert intent == "time"
        assert "yes" in response.lower() or "confirm" in response.lower() or "shall" in response.lower()

    def test_process_confirm_flow(self):
        self.dlg.auth_success()
        self.dlg.process("tell me the time")   # sets CONFIRMING
        intent, _ = self.dlg.process("yes")
        assert intent == "confirm"

    def test_process_cancel_flow(self):
        self.dlg.auth_success()
        self.dlg.process("tell me a joke")
        intent, _ = self.dlg.process("no")
        assert intent == "cancel"

    def test_process_unknown(self):
        self.dlg.auth_success()
        intent, _ = self.dlg.process("xyzzy foobar 999")
        assert intent == "unknown"

    def test_history_recorded(self):
        self.dlg.greet()
        self.dlg.auth_success()
        self.dlg.process("hello")
        assert len(self.dlg.get_history()) > 0

    def test_reset_clears_state(self):
        self.dlg.auth_success()
        self.dlg.reset()
        assert self.dlg.ctx.state == DialogState.IDLE
        assert self.dlg.ctx.turn_count == 0

    def test_farewell(self):
        msg = self.dlg.farewell()
        assert "goodbye" in msg.lower() or "see you" in msg.lower() or "logging" in msg.lower()


# ══════════════════════════════════════════════
#  CommandExecutor
# ══════════════════════════════════════════════

class TestCommandExecutor:
    def setup_method(self):
        self.ex = CommandExecutor()

    def test_time(self):
        r = self.ex.execute("what time is it")
        assert r.success
        assert "time" in r.output.lower()

    def test_date(self):
        r = self.ex.execute("what date is today")
        assert r.success
        assert "today" in r.output.lower() or r.intent == "date"

    def test_joke(self):
        r = self.ex.execute("tell me a joke")
        assert r.success
        assert len(r.output) > 10

    def test_calculate_addition(self):
        r = self.ex.execute("calculate 10 + 5")
        assert r.success
        assert "15" in r.output

    def test_calculate_multiplication(self):
        r = self.ex.execute("calculate 6 * 7")
        assert r.success
        assert "42" in r.output

    def test_calculate_bad_expr(self):
        r = self.ex.execute("calculate abc xyz")
        assert not r.success

    def test_unknown_command(self):
        r = self.ex.execute("xyzzy impossible command 99999")
        assert not r.success

    def test_execution_result_str(self):
        r = self.ex.execute("tell me the time")
        s = str(r)
        assert "✓" in s or "✗" in s


# ══════════════════════════════════════════════
#  End-to-End Integration (simulated, no I/O)
# ══════════════════════════════════════════════

class TestEndToEnd:
    """Simulate the full pipeline without camera / mic / TTS."""

    def test_full_pipeline_simulated(self):
        auth    = FaceAuthenticator(simulated=True)
        dialog  = DialogEngine(username="IntegrationUser")
        executor= CommandExecutor()

        # Enroll
        assert auth.enroll()

        # Auth
        assert auth.authenticate()
        dialog.auth_success()
        assert dialog.ctx.state == DialogState.READY

        # Command: time
        intent, resp = dialog.process("what time is it")
        assert intent == "time"

        # Confirm
        intent2, resp2 = dialog.process("yes")
        assert intent2 == "confirm"

        # Execute
        result = executor.execute(dialog.ctx.last_command)
        assert result.success

        # Exit
        intent3, _ = dialog.process("exit")
        assert intent3 == "exit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
