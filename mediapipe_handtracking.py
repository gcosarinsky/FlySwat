import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Configure the modern Hand Landmarker options
base_options = python.BaseOptions(
    model_asset_path=r"D:\HandTracking_example\models\hand_landmarker.task"
)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,  # Mode intended for frame-by-frame processing
    num_hands=2,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7
)

# 2. Initialize the detector and the camera
detector = vision.HandLandmarker.create_from_options(options)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Mirror the image for the user's convenience
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # Convert from BGR (OpenCV) to RGB (MediaPipe)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Modern MediaPipe requires wrapping the image in its own object format
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    # Compute a timestamp in milliseconds (required in VIDEO mode)
    timestamp_ms = int(time.time() * 1000)

    # 3. Process the frame
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    # 4. Draw the results if hands are detected
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            # Draw individual landmarks
            for landmark in hand_landmarks:
                cx, cy = int(landmark.x * w), int(landmark.y * h)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

            # Get the index fingertip coordinates (landmark index 8)
            index_finger_tip = hand_landmarks[8]
            x_idx = index_finger_tip.x * w
            y_idx = index_finger_tip.y * h
            
            # Use x_idx and y_idx here to control your game

    # Show window
    cv2.imshow("Modern Hand Tracking", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# 5. Clean up resources
detector.close()
cap.release()
cv2.destroyAllWindows()
