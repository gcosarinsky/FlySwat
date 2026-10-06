import cv2

# 1. Inicializar la captura de la webcam
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("No se pudo recibir el fotograma.")
        break

    # 2. Voltear en espejo (más natural para webcam)
    frame = cv2.flip(frame, 1)

    # 3. Mostrar el stream de video en vivo
    cv2.imshow("Stream de Video", frame)

    # 4. Salir si se presiona la tecla 'q'
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# 5. Liberar recursos
cap.release()
cv2.destroyAllWindows()
