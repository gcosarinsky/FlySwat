import cv2

# 1. Initialize webcam capture
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Could not receive a frame.")
        break

    # 2. Mirror the image (more natural for a webcam)
    frame = cv2.flip(frame, 1)

    # 3. Show the live video stream
    cv2.imshow("Video Stream", frame)

    # 4. Exit when the 'q' key is pressed
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# 5. Release resources
cap.release()
cv2.destroyAllWindows()
