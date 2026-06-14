"""
modules/stt.py  —  Speech Input Wrapper
========================================
Wraps SpeechRecognition with a keyboard-input fallback.
The rest of the system always calls get_input() and never
needs to know whether audio or keyboard is being used.
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr  # type: ignore
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False
    logger.warning("[STT] SpeechRecognition not found – keyboard fallback active.")


class SpeechInput:
    """
    Get user input either from microphone or keyboard.

    Args:
        use_mic:  Force microphone use (falls back to keyboard if unavailable).
        timeout:  Seconds to wait for speech before giving up.
    """

    def __init__(self, use_mic: bool = True, timeout: int = 6):
        self.use_mic = use_mic and _SR_AVAILABLE
        self.timeout = timeout
        if self.use_mic:
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            logger.info("[STT] Microphone mode active.")
        else:
            logger.info("[STT] Keyboard fallback mode active.")

    def get_input(self, prompt: str = "👤 You: ") -> str | None:
        """Return transcribed text or None if nothing understood."""
        if not self.use_mic:
            return self._keyboard(prompt)

        print("🎤  Listening…", flush=True)
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self._recognizer.listen(
                    source, timeout=self.timeout, phrase_time_limit=8
                )
        except sr.WaitTimeoutError:
            logger.info("[STT] No speech detected (timeout).")
            return None
        except Exception as exc:
            logger.warning(f"[STT] Mic error: {exc}")
            return self._keyboard(prompt)

        for engine, fn in [
            ("Google",  lambda a: self._recognizer.recognize_google(a)),
            ("Sphinx",  lambda a: self._recognizer.recognize_sphinx(a)),
        ]:
            try:
                text = fn(audio).lower().strip()
                logger.info(f"[STT] Recognised [{engine}]: {text}")
                return text
            except sr.UnknownValueError:
                pass
            except Exception as exc:
                logger.debug(f"[STT] {engine} unavailable: {exc}")

        logger.info("[STT] Could not recognise speech.")
        return None

    @staticmethod
    def _keyboard(prompt: str) -> str | None:
        try:
            return input(prompt).strip() or None
        except (EOFError, KeyboardInterrupt):
            return "exit"
