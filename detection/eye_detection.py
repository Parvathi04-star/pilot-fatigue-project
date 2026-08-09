import csv
import json
import os
import sys
import time
from datetime import datetime

import cv2
import mediapipe as mp

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from logic.timer_system import check_face_presence
from logic.fatigue_logic import check_fatigue, calculate_fatigue_score
from logic.alert_system import warning
from logic.face_metrics import calculate_mar

LIVE_DATA_FILE = os.path.join(PROJECT_ROOT, "live_data.json")
LIVE_FRAME_FILE = os.path.join(PROJECT_ROOT, "live_frame.jpg")
FATIGUE_LOG_FILE = os.path.join(PROJECT_ROOT, "fatigue_log.csv")

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("Camera could not be opened!")
    raise SystemExit(1)

mesh = mp.solutions.face_mesh.FaceMesh(max_num_faces=1)

closed_frames = 0
fps = 30
start_time = time.time()
blink_reset_time = time.time()
closed_start_time = None

fatigue_score = 0
blink_count = 0
previous_closed = False

session_start = datetime.now()
max_fatigue_score = 0
yawn_count = 0

head_status = "UNKNOWN"
status = "NO FACE"
eye_state = "OPEN"
yawn_status = False
yawn_start_time = None

print("Starting detection...")

try:
    while True:
        fatigue_score = 0
        success, frame = camera.read()

        if not success:
            print("Camera read failed.")
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mesh.process(rgb)
        h, w, _ = frame.shape
        face_found = False
        elapsed_time = int(time.time() - start_time)

        if time.time() - blink_reset_time >= 60:
            blink_count = 0
            blink_reset_time = time.time()

        # Defaults for a frame with no detected face.
        head_status = "UNKNOWN"
        eye_state = "OPEN"
        status = "NO FACE"

        if results.multi_face_landmarks:
            face_found = True

            for face in results.multi_face_landmarks:
                landmarks = face.landmark
                nose = landmarks[1]
                left_face = landmarks[234]
                right_face = landmarks[454]

                top = landmarks[160]
                bottom = landmarks[144]
                top_y = int(top.y * h)
                bottom_y = int(bottom.y * h)
                eye_distance = abs(bottom_y - top_y)

                nose_x = int(nose.x * w)
                left_x = int(left_face.x * w)
                right_x = int(right_face.x * w)
                face_center = (left_x + right_x) // 2

                head_status = "STRAIGHT"

                # Yawn detection
                mar = calculate_mar(landmarks)

                if mar > 0.6:
                    if yawn_start_time is None:
                        yawn_start_time = time.time()

                    if time.time() - yawn_start_time > 1 and not yawn_status:
                        yawn_count += 1
                        yawn_status = True
                else:
                    yawn_start_time = None
                    yawn_status = False

                # Simple horizontal head-direction estimate
                if nose_x < face_center - 25:
                    head_status = "LEFT"
                elif nose_x > face_center + 25:
                    head_status = "RIGHT"

                # Eye closure / fatigue
                if eye_distance < 10:
                    eye_state = "CLOSED"
                    closed_frames += 1

                    if not previous_closed:
                        previous_closed = True
                        closed_start_time = time.time()

                    eye_closed_time = closed_frames / fps
                    fatigue_score = calculate_fatigue_score(
                        eye_closed_time,
                        blink_count
                    )
                    max_fatigue_score = max(max_fatigue_score, fatigue_score)
                    status = check_fatigue(fatigue_score)

                    if status == "WARNING":
                        cv2.putText(
                            frame, "FATIGUE WARNING", (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1,
                            (0, 165, 255), 3
                        )
                    elif status == "DROWSY":
                        warning(status)
                        cv2.putText(
                            frame, "DROWSY ALERT!", (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 1,
                            (0, 0, 255), 3
                        )

                    cv2.putText(
                        frame, "EYE CLOSED", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 0, 255), 2
                    )
                else:
                    eye_state = "OPEN"
                    closed_frames = 0

                    if previous_closed and closed_start_time is not None:
                        duration = time.time() - closed_start_time
                        if 0.05 <= duration <= 0.5:
                            blink_count += 1
                        previous_closed = False
                        closed_start_time = None

                    status = "ACTIVE"

                    cv2.putText(
                        frame, "EYE OPEN", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 255, 0), 2
                    )

                cv2.putText(
                    frame, status, (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 0), 2
                )
                cv2.putText(
                    frame, f"Dist: {eye_distance}", (50, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2
                )
                cv2.putText(
                    frame, f"Blinks: {blink_count}", (50, 250),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 255), 2
                )
                cv2.putText(
                    frame, f"Time: {elapsed_time}s", (50, 300),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 255), 2
                )
                cv2.putText(
                    frame, f"Score: {fatigue_score}", (50, 350),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (0, 255, 255), 2
                )
                cv2.putText(
                    frame, f"Head: {head_status}", (50, 400),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 0), 2
                )
                cv2.putText(
                    frame, f"Yawns: {yawn_count}", (50, 450),
                    cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 0, 255), 2
                )

                for point in LEFT_EYE + RIGHT_EYE:
                    landmark = landmarks[point]
                    x = int(landmark.x * w)
                    y = int(landmark.y * h)
                    cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

        # Face-presence warning is displayed after detection.
        if check_face_presence(face_found):
            status = "NO FACE"
            cv2.putText(
                frame, "NO FACE DETECTED", (50, 500),
                cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 0, 255), 3
            )

        # ISO-8601 UTC timestamp with explicit Z suffix.
        current_time = datetime.now().astimezone().isoformat(timespec="seconds")

        live_data = {
            "timestamp": current_time,
            "session_time": elapsed_time,
            "eyes": eye_state,
            "head": head_status,
            "blinks": blink_count,
            "yawns": yawn_count,
            "fatigue_score": fatigue_score,
            "status": status
        }

        with open(LIVE_DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(live_data, file, indent=4)

        # This file is runtime-only and is ignored by Git.
        cv2.imwrite(LIVE_FRAME_FILE, frame)

        cv2.imshow("Eye Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    session_end = datetime.now()
    session_duration = session_end - session_start

    file_exists = os.path.isfile(FATIGUE_LOG_FILE)

    with open(FATIGUE_LOG_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "Date",
                "Session Time",
                "Blink Count",
                "Yawns",
                "Fatigue Score"
            ])

        writer.writerow([
            session_start.strftime("%Y-%m-%d"),
            str(session_duration),
            blink_count,
            yawn_count,
            max_fatigue_score
        ])

    camera.release()
    cv2.destroyAllWindows()
