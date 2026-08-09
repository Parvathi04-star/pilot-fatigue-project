import cv2
import mediapipe as mp
import numpy as np
import time
import sys
import os

yawn_start_time = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from logic.face_metrics import calculate_mar

camera = cv2.VideoCapture(0)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1)
mp_draw = mp.solutions.drawing_utils

# -------------------------------
# Blink detection variables
# -------------------------------
blink_count = 0
eye_closed = False
closed_frames = 0

EAR_THRESHOLD = 0.23

# -------------------------------
# Yawn detection variables
# -------------------------------
yawn_count = 0
yawn_status = False

fatigue_score = 0

blink_penalty = 0
eye_closure_penalty = 0
yawn_penalty = 0
head_down_penalty = 0
# -------------------------------
# Head movement tracking
# -------------------------------
previous_nose = None

# -------------------------------
# Simple distance function
# -------------------------------
def distance(p1, p2):
    return np.linalg.norm(np.array(p1) - np.array(p2))


while True:

    success, frame = camera.read()
    if not success:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if results.multi_face_landmarks:

        for face in results.multi_face_landmarks:

            h, w, _ = frame.shape
            landmarks = face.landmark
            mar = calculate_mar(landmarks)

            # -------------------------------
            # Yawn Detection Logic
            # -------------------------------
            if mar > 0.6:

                if yawn_start_time is None:
                    yawn_start_time = time.time()

                if time.time() - yawn_start_time > 1.0 and not yawn_status:
                         yawn_count += 1
                         yawn_status = True

                yawn_penalty = min(yawn_count * 10, 30)

                cv2.putText(frame, "YAWNING", (30, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            else:
                yawn_start_time = None
                yawn_status = False

            # -------------------------------
            # HEAD MOVEMENT FILTER (ADDED)
            # -------------------------------
            nose = landmarks[1]
            current_nose = (int(nose.x * w), int(nose.y * h))

            if previous_nose is not None:
                movement = distance(current_nose, previous_nose)

                if movement > 15:
                    previous_nose = current_nose
                    continue  # skip frame if head moved too much

            previous_nose = current_nose

            # -------------------------------
            # LEFT EYE LANDMARKS
            # -------------------------------
           # LEFT EYE
            left_up = (int(landmarks[159].x * w), int(landmarks[159].y * h))
            left_down = (int(landmarks[145].x * w), int(landmarks[145].y * h))
            left_left = (int(landmarks[33].x * w), int(landmarks[33].y * h))
            left_right = (int(landmarks[133].x * w), int(landmarks[133].y * h))

            # RIGHT EYE
            right_up = (int(landmarks[386].x * w), int(landmarks[386].y * h))
            right_down = (int(landmarks[374].x * w), int(landmarks[374].y * h))
            right_left = (int(landmarks[362].x * w), int(landmarks[362].y * h))
            right_right = (int(landmarks[263].x * w), int(landmarks[263].y * h))

            left_ear = distance(left_up, left_down) / distance(left_left, left_right)

            right_ear = distance(right_up, right_down) / distance(right_left, right_right)

            ear = (left_ear + right_ear) / 2

            # -------------------------------
            # BLINK LOGIC
            # -------------------------------
            if ear < EAR_THRESHOLD:

                closed_frames += 1

                if closed_frames > 90:
                    eye_closure_penalty = 60
                elif closed_frames > 60:
                    eye_closure_penalty = 40
                elif closed_frames > 30:
                    eye_closure_penalty = 20

                if not eye_closed:
                    eye_closed = True

            else:

                if eye_closed:
                    blink_count += 1
                    eye_closed = False

                closed_frames = 0
                eye_closure_penalty = 0

            if blink_count < 5:
                blink_penalty = 10
            elif blink_count < 10:
                blink_penalty = 5
            else:
                blink_penalty = 0

            fatigue_score = (
                blink_penalty +
                eye_closure_penalty +
                yawn_penalty +
                head_down_penalty
            )

            fatigue_score = min(fatigue_score, 100)

            if fatigue_score <= 30:
                status = "ACTIVE"

            elif fatigue_score <= 60:
                status = "TIRED"

            elif fatigue_score <= 80:
                status = "FATIGUED"

            else:
                status = "CRITICAL"

            # -------------------------------
            # DRAW
            # -------------------------------
            mp_draw.draw_landmarks(
                frame,
                face,
                mp_face_mesh.FACEMESH_TESSELATION
            )

            cv2.putText(frame, f"EAR: {round(ear, 2)}", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.putText(frame, f"Blinks: {blink_count}", (30, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            cv2.putText(frame, f"Yawns: {yawn_count}", (30, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            
            cv2.putText(frame, f"Score: {fatigue_score}", (30, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

            cv2.putText(frame, f"Status: {status}", (30, 200),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Landmarks", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()