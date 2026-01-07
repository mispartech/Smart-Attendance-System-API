import numpy as np
from django.utils import timezone

from attendanceapi.models import FaceEmbedding, TempUser, TempAttendance
from attendanceapi.utils import get_face_app

from scipy.spatial.distance import cosine


def recognize_faces_from_frame(frame, threshold=0.5):
    """
    Core face recognition logic.
    This function does NOT handle HTTP or database writes.
    """

    app = get_face_app()
    detected_faces = app.get(frame)

    results = []

    if not detected_faces:
        return results

    embeddings = FaceEmbedding.objects.select_related("user").all()

    for face in detected_faces:
        best_match = None
        best_distance = float("inf")

        for record in embeddings:
            distance = cosine(
                np.array(record.embedding),
                face.embedding
            )

            if distance < best_distance:
                best_distance = distance
                best_match = record

        if best_match and best_distance <= threshold:
            results.append({
                "recognized": True,
                "user_id": str(best_match.user.id),
                "confidence": round(1 - best_distance, 3),
            })
        else:
            results.append({
                "recognized": False,
                "confidence": None,
            })

    return results


TEMP_THRESHOLD = 0.65

def match_or_create_temp_user(embedding):
    """
    Match unrecognized face to existing TempUser or create a new one.
    Returns (temp_user, created)
    """

    temps = TempUser.objects.all()

    best_match = None
    best_distance = float("inf")

    for temp in temps:
        stored_embedding = np.array(temp.face_embedding)
        dist = cosine(embedding, stored_embedding)

        if dist < best_distance:
            best_distance = dist
            best_match = temp

    if best_match and best_distance < TEMP_THRESHOLD:
        best_match.appearances += 1
        best_match.save()
        return best_match, False

    return TempUser.objects.create(
        face_embedding=embedding.tolist()
    ), True

def extract_face_embedding(frame_data):
    """
    Accepts base64 image string.
    Returns a mock embedding for now.
    """
    if not frame_data:
        return None

    # TEMP: mock embedding (replace later with real model)
    return [0.01] * 128


def recognize_face(embedding):
    """
    Attempts to match embedding with registered users.
    Returns user object or None.
    """
    # TEMP: no registered user match
    return None


def match_or_create_temp_user(embedding):
    """
    Matches embedding with temp users or creates new one.
    """
    from attendanceapi.models import TemporaryUser

    temp_user, created = TemporaryUser.objects.get_or_create(
        default=True  # placeholder logic
    )

    temp_user.appearances += 1
    temp_user.save()

    return temp_user, created