import cv2
import mediapipe as mp

camera = cv2.VideoCapture(0)

mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection()

mp_draw = mp.solutions.drawing_utils

previous_nose = None

while True:

    success, frame = camera.read()

    if not success:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = face_detector.process(rgb)

    if results.detections:

        for detection in results.detections:

            mp_draw.draw_detection(
                frame,
                detection
            )

    cv2.imshow("Face Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()