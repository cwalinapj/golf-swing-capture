"""Golf swing video recorder using OpenCV."""

import os
import threading
import time
from datetime import datetime

import cv2

from capture.config import Config


class GolfSwingRecorder:
    """Captures and records golf swing video from a camera."""

    def __init__(self, config: Config | None = None):
        self._config = config or Config()
        self._camera: cv2.VideoCapture | None = None
        self._writer: cv2.VideoWriter | None = None
        self._lock = threading.Lock()
        self._is_recording = False
        self._current_file: str | None = None
        os.makedirs(self._config.OUTPUT_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Camera lifecycle
    # ------------------------------------------------------------------

    def open(self) -> bool:
        """Open the camera. Returns True on success."""
        with self._lock:
            if self._camera and self._camera.isOpened():
                return True
            cap = cv2.VideoCapture(self._config.CAMERA_INDEX)
            if not cap.isOpened():
                return False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.FRAME_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, self._config.FPS)
            self._camera = cap
            return True

    def close(self) -> None:
        """Stop any active recording and release the camera."""
        self.stop_recording()
        with self._lock:
            if self._camera:
                self._camera.release()
                self._camera = None

    # ------------------------------------------------------------------
    # Frame capture
    # ------------------------------------------------------------------

    def get_frame(self) -> bytes | None:
        """
        Read one frame from the camera and return it as a JPEG byte string,
        or None if the camera is unavailable.
        """
        with self._lock:
            if not self._camera or not self._camera.isOpened():
                return None
            ret, frame = self._camera.read()
            if not ret:
                return None
            if self._is_recording and self._writer:
                self._writer.write(frame)
            _, buffer = cv2.imencode(".jpg", frame)
            return buffer.tobytes()

    # ------------------------------------------------------------------
    # Recording control
    # ------------------------------------------------------------------

    def start_recording(self) -> str | None:
        """
        Begin writing frames to a new video file.
        Returns the output file path, or None if already recording / camera
        is not open.
        """
        with self._lock:
            if self._is_recording:
                return None
            if not self._camera or not self._camera.isOpened():
                return None
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(
                self._config.OUTPUT_DIR,
                f"swing_{timestamp}{self._config.VIDEO_EXTENSION}",
            )
            fourcc = cv2.VideoWriter_fourcc(*self._config.VIDEO_CODEC)
            width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self._camera.get(cv2.CAP_PROP_FPS) or self._config.FPS
            self._writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
            self._is_recording = True
            self._current_file = filename
            return filename

    def stop_recording(self) -> str | None:
        """
        Stop the current recording and flush the file.
        Returns the path of the saved file, or None if not recording.
        """
        with self._lock:
            if not self._is_recording:
                return None
            self._is_recording = False
            if self._writer:
                self._writer.release()
                self._writer = None
            saved = self._current_file
            self._current_file = None
            return saved

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._is_recording

    @property
    def current_file(self) -> str | None:
        with self._lock:
            return self._current_file
