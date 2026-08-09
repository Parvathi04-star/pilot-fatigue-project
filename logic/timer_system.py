import time

face_missing_start = None


def check_face_presence(face_found):

    global face_missing_start

    if face_found:

        face_missing_start = None
        return False

    if face_missing_start is None:

        face_missing_start = time.time()

    elapsed = time.time() - face_missing_start

    if elapsed > 3:
        return True

    return False