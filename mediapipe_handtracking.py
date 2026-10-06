import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Configurar las opciones del Hand Landmarker moderno
base_options = python.BaseOptions(
    model_asset_path=r"D:\HandTracking_example\models\hand_landmarker.task"
)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,  # Modo específico para procesamiento frame a frame
    num_hands=2,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7
)

# 2. Inicializar el detector y la cámara
detector = vision.HandLandmarker.create_from_options(options)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Voltear en espejo para comodidad del usuario
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # Convertir de BGR (OpenCV) a RGB (MediaPipe)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # MediaPipe moderno requiere convertir la imagen a su propio formato de objeto
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    # Calcular una marca de tiempo en milisegundos (obligatoria en modo VIDEO)
    timestamp_ms = int(time.time() * 1000)

    # 3. Procesar el frame
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    # 4. Dibujar los resultados si se detectan manos
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            # Dibujar puntos individuales
            for landmark in hand_landmarks:
                cx, cy = int(landmark.x * w), int(landmark.y * h)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

            # Obtener las coordenadas del dedo índice (Landmark índice 8)
            index_finger_tip = hand_landmarks[8]
            x_idx = index_finger_tip.x * w
            y_idx = index_finger_tip.y * h
            
            # Aquí puedes usar x_idx e y_idx para el control de tu juego

    # Mostrar ventana
    cv2.imshow("Hand Tracking Moderno", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# 5. Limpieza limpia de recursos
detector.close()
cap.release()
cv2.destroyAllWindows()
