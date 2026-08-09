def calculate_fatigue_score(
    eye_closed_time,
    blink_count
):

    fatigue_score = 0

    if eye_closed_time > 1:
        fatigue_score += 20

    if eye_closed_time > 2:
        fatigue_score += 30

    if eye_closed_time > 3:
        fatigue_score += 30

    if blink_count < 5:
        fatigue_score += 20

    return fatigue_score


def check_fatigue(
    fatigue_score
):

    if fatigue_score >= 70:
        return "DROWSY"

    elif fatigue_score >= 40:
        return "WARNING"

    return "ACTIVE"