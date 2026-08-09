"""Shared facial measurement utilities used by detection modules."""


def calculate_mar(landmarks):
    """Calculate Mouth Aspect Ratio from MediaPipe face landmarks."""
    upper_lip = landmarks[13]
    lower_lip = landmarks[14]
    left_corner = landmarks[61]
    right_corner = landmarks[291]

    vertical = abs(lower_lip.y - upper_lip.y)
    horizontal = abs(right_corner.x - left_corner.x)

    if horizontal == 0:
        return 0.0

    return vertical / horizontal
