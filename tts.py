"""
modules/tts.py  —  Text-to-Speech Wrapper
==========================================
Thin adapter over pyttsx3 (offline) with gTTS fallback.
Always prints to console regardless of audio availability.
"""

from __future__ import annotations
import logging
import sys

logger = logging.getLogger(__name__)

try:
    import pyttsx3  # type: ignore
    _PYTTSX3 = True
except ImportError:
    _PYTTSX3 = False
    logger.warning("[TTS] pyttsx3 not found – audio disabled.")


class Speaker:
    """
    Speak text aloud (and always echo to stdout).

    Args:
        enabled:  Set False to suppress audio entirely (text-only).
        rate:     Words per minute (default 170).
    """

    def __init__(self, enabled: bool = True, rate: int = 170):
        self.enabled = enabled and _PYTTSX3
        self._engine = None
        if self.enabled:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", rate)
                voices = engine.getProperty("voices")
                for v in voices:
                    if "female" in v.name.lower() or "zira" in v.name.lower():
                        engine.setProperty("voice", v.id)
                        break
                self._engine = engine
                logger.info("[TTS] pyttsx3 initialised.")
            except Exception as exc:
                logger.warning(f"[TTS] pyttsx3 init error: {exc}")
                self.enabled = False

    def say(self, text: str):
        print(f"\n🤖  {text}\n", flush=True)
        logger.info(f"[TTS] say: {text}")
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as exc:
                logger.warning(f"[TTS] speak error: {exc}")

    def __call__(self, text: str):
        self.say(text)
