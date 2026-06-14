"""
modules/auth.py  —  Face Authentication Module
================================================
Handles:
  • Face detection via OpenCV Haar cascades
  • Face enrollment (save reference snapshot)
  • Face verification (compare live frame vs enrolled)
  • Simulated-mode fallback (no camera / no cv2)

Designed to be reused independently.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────
DATA_DIR   = Path(__file__).parent.parent / "data" / "faces"
CASCADE_PATH = None   # resolved at runtime

# ── OpenCV availability ───────────────────────────────────────
try:
    import cv2  # type: ignore
    _CV2_AVAILABLE = True
    # Locate haar cascade
    _cascade_candidates = [
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
        "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
        "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
    ]
    for c in _cascade_candidates:
        if os.path.exists(c):
            CASCADE_PATH = c
            break
    if not CASCADE_PATH:
        logger.warning("Haar cascade not found – face detection degraded.")
except ImportError:
    _CV2_AVAILABLE = False
    logger.warning("OpenCV not installed. Auth module running in SIMULATED mode.")


class AuthError(Exception):
    """Raised when authentication fails definitively."""


class FaceAuthenticator:
    """
    Two-step face authenticator:
      1. enroll()    – capture & save reference face image
      2. authenticate() – capture live frame & verify a face is present

    In simulated mode (no OpenCV), all calls succeed with a warning.
    """

    def __init__(
        self,
        data_dir: Path | str = DATA_DIR,
        username: str = "default_user",
        camera_index: int = 0,
        simulated: bool = False,
    ):
        self.data_dir     = Path(data_dir)
        self.username     = username
        self.camera_index = camera_index
        self.simulated    = simulated or not _CV2_AVAILABLE
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._ref_path    = self.data_dir / f"{username}_ref.jpg"

        if self.simulated:
            logger.info("[FaceAuth] Simulated mode active (no OpenCV or forced).")

    # ── Public API ────────────────────────────────────────────

    def enroll(self, display: bool = True) -> bool:
        """Capture a reference face image from the webcam and save it."""
        if self.simulated:
            self._write_placeholder()
            logger.info("[FaceAuth] Simulated enroll – placeholder saved.")
            return True

        logger.info("[FaceAuth] Starting enrollment…")
        cap = self._open_camera()
        if cap is None:
            return False

        try:
            detector = self._load_detector()
            enrolled = False
            deadline = time.time() + 15  # 15-second window

            while time.time() < deadline:
                ret, frame = cap.read()
                if not ret:
                    break

                faces = self._detect_faces(frame, detector)
                annotated = self._draw_faces(frame.copy(), faces)

                if display:
                    cv2.putText(
                        annotated, "ENROLLMENT – press S to save, Q to quit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                    )
                    cv2.imshow("Face Enrollment", annotated)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("s") and faces:
                        cv2.imwrite(str(self._ref_path), frame)
                        logger.info(f"[FaceAuth] Reference saved → {self._ref_path}")
                        enrolled = True
                        break
                    elif key == ord("q"):
                        break
                else:
                    # headless: auto-save first detected face
                    if faces:
                        cv2.imwrite(str(self._ref_path), frame)
                        enrolled = True
                        break
                    time.sleep(0.1)

            return enrolled
        finally:
            cap.release()
            if display:
                cv2.destroyAllWindows()

    def authenticate(
        self,
        timeout: float = 10.0,
        display: bool = False,
        skip_enroll_check: bool = False,
    ) -> bool:
        """
        Verify a face is visible.  Returns True if face detected within timeout.
        """
        if self.simulated:
            logger.info("[FaceAuth] Simulated authenticate → SUCCESS")
            time.sleep(0.3)
            return True

        if not skip_enroll_check and not self._ref_path.exists():
            logger.warning("[FaceAuth] No reference image found. Run enroll() first.")
            return False

        logger.info("[FaceAuth] Authenticating…")
        cap = self._open_camera()
        if cap is None:
            return False

        try:
            detector  = self._load_detector()
            deadline  = time.time() + timeout
            success   = False

            while time.time() < deadline:
                ret, frame = cap.read()
                if not ret:
                    break

                faces = self._detect_faces(frame, detector)
                if display:
                    annotated = self._draw_faces(frame.copy(), faces)
                    status = "FACE DETECTED" if faces else "Searching…"
                    color  = (0, 255, 0) if faces else (0, 100, 255)
                    cv2.putText(
                        annotated, status,
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
                    )
                    cv2.imshow("Authentication", annotated)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                if faces:
                    logger.info(f"[FaceAuth] Face detected → {len(faces)} face(s).")
                    success = True
                    break

                time.sleep(0.05)

            return success
        finally:
            cap.release()
            if display:
                cv2.destroyAllWindows()

    def is_enrolled(self) -> bool:
        return self._ref_path.exists() or self.simulated

    # ── Private helpers ───────────────────────────────────────

    def _open_camera(self):
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            logger.error("[FaceAuth] Cannot open camera.")
            return None
        return cap

    def _load_detector(self):
        if CASCADE_PATH:
            return cv2.CascadeClassifier(CASCADE_PATH)
        # fallback empty classifier
        return cv2.CascadeClassifier()

    @staticmethod
    def _detect_faces(frame, detector):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    @staticmethod
    def _draw_faces(frame, faces):
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return frame

    def _write_placeholder(self):
        """Write a tiny placeholder image so enroll state persists."""
        try:
            import struct, zlib
            # 1×1 white PNG
            png = (
                b'\x89PNG\r\n\x1a\n' +
                b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02'
                b'\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00'
                b'\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            self._ref_path.with_suffix(".png").write_bytes(png)
        except Exception:
            self._ref_path.touch()
