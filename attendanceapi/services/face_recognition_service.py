import numpy as np
from django.utils import timezone

from attendanceapi.models import FaceEmbedding, TempUser, TempAttendance
from scipy.spatial.distance import cosine
from attendanceapi.services.face_model import get_face_app
from django.utils.crypto import get_random_string

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

    # Generate a **unique temporary email** for new TempUser
    unique_email = f"temp_{get_random_string(12)}@mispartechnologies.com"

    temp_user, created = TempUser.objects.get_or_create(
        temp_email=unique_email,
        defaults={
            "face_embedding": embedding.tolist(),
            "appearances": 1
        }
    )
    return temp_user, created

def extract_face_embedding(frame):
    """
    Accepts an OpenCV image (np.ndarray).
    Returns a single face embedding or None if no face is detected.
    """

    if frame is None:
        return None

    if not isinstance(frame, np.ndarray):
        raise TypeError(
            f"Expected OpenCV frame (np.ndarray), got {type(frame)}"
        )

    if frame.size == 0:
        return None

    app = get_face_app()
    detected_faces = app.get(frame)

    if not detected_faces:
        return None

    # Take the most confident / first detected face
    face = detected_faces[0]

    if not hasattr(face, "embedding") or face.embedding is None:
        return None

    return np.array(face.embedding)

def recognize_face(embedding):
    """
    Attempts to match embedding with registered users.
    Returns user object or None.
    """
    # TEMP: no registered user match
    return None

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