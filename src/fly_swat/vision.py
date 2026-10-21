"""Webcam and MediaPipe hand landmark extraction."""

from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from fly_swat.gestures import RawHand, distance

DEFAULT_MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "hand_landmarker.task"

# MediaPipe hand landmark indices.
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_MCP = 9


class HandDetector:
    """Detects up to two hands and returns them in pixel coordinates.

    Frames must be the mirrored BGR image shown to the player, so the returned
    positions match what is drawn on screen.
    """

    def __init__(self, model_path: Path | str = DEFAULT_MODEL_PATH, num_hands: int = 2):
        model_path = Path(model_path)
        if not model_path.is_file():
            raise FileNotFoundError(f"Hand landmarker model not found: {model_path}")
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def detect(self, frame_bgr, timestamp_ms: int) -> list[RawHand]:
        """Return the hands found in the frame. Timestamps must increase."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, timestamp_ms)

        hands = []
        for i, landmarks in enumerate(result.hand_landmarks):
            def px(index):
                return (landmarks[index].x * w, landmarks[index].y * h)

            category = result.handedness[i][0] if i < len(result.handedness) else None
            hands.append(
                RawHand(
                    thumb_tip=px(THUMB_TIP),
                    index_tip=px(INDEX_TIP),
                    ref_size=distance(px(WRIST), px(MIDDLE_MCP)),
                    label=category.category_name if category else "",
                    score=category.score if category else 1.0,
                )
            )
        return hands

    def close(self):
        self._landmarker.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def open_camera(index: int = 0) -> cv2.VideoCapture:
    """Open the webcam or raise RuntimeError if it is not available."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open camera {index}.")
    return cap
