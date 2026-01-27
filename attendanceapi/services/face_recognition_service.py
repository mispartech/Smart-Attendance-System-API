# -------------------------------
# In-memory short-term face cache
# -------------------------------
FACE_STABILITY_CACHE = {}
FACE_CONFIRMATION_FRAMES = 3
FACE_CACHE_TTL_SECONDS = 5

import numpy as np
from django.utils import timezone
from attendanceapi.models import FaceEmbedding, TempUser, TempAttendance
from scipy.spatial.distance import cosine
from attendanceapi.services.face_model import get_face_app
from django.utils.crypto import get_random_string

def _embedding_key(embedding, precision=2):
    """
    Reduce embedding noise to allow stable hashing.
    """
    return tuple(np.round(embedding, precision))

def _cleanup_face_cache():
    now = timezone.now()
    expired = [
        k for k, v in FACE_STABILITY_CACHE.items()
        if (now - v["last_seen"]).total_seconds() > FACE_CACHE_TTL_SECONDS
    ]
    for k in expired:
        del FACE_STABILITY_CACHE[k]

def recognize_faces_from_frame(frame, threshold=0.5):
    """
    Attendance-grade face recognition with temporal stability.
    """

    app = get_face_app()
    detected_faces = app.get(frame)

    if not detected_faces:
        return []

    _cleanup_face_cache()

    embeddings_db = FaceEmbedding.objects.select_related("user").all()
    results = []

    for face in detected_faces:
        embedding = np.array(face.embedding)
        emb_key = _embedding_key(embedding)

        # ------------------------------------
        # Step 1: DB match (registered users)
        # ------------------------------------
        best_match = None
        best_distance = float("inf")

        for record in embeddings_db:
            dist = cosine(np.array(record.embedding), embedding)
            if dist < best_distance:
                best_distance = dist
                best_match = record

        # ------------------------------------
        # Step 2: Update stability cache
        # ------------------------------------
        cache = FACE_STABILITY_CACHE.get(emb_key)

        if not cache:
            FACE_STABILITY_CACHE[emb_key] = {
                "count": 1,
                "last_seen": timezone.now(),
                "best_match": best_match,
                "best_distance": best_distance,
            }
            continue

        cache["count"] += 1
        cache["last_seen"] = timezone.now()

        # ------------------------------------
        # Step 3: Confirm recognition
        # ------------------------------------
        bbox = face.bbox.astype(int).tolist()

        if cache["count"] >= FACE_CONFIRMATION_FRAMES:
            if best_match and best_distance <= threshold:
                results.append({
                    "recognized": True,
                    "user": best_match.user,
                    "distance": best_distance,
                    "bbox": bbox,
                })

            else:
                results.append({
                    "recognized": False,
                    "embedding": embedding,
                    "bbox": bbox,
                })

    return results

def match_or_create_temp_user(embedding):
    """
    Attendance-grade unknown face handling.
    """

    _cleanup_face_cache()
    emb_key = _embedding_key(embedding)

    # Only create temp user AFTER stability
    cache = FACE_STABILITY_CACHE.get(emb_key)
    if not cache or cache["count"] < FACE_CONFIRMATION_FRAMES:
        return None, False

    temps = TempUser.objects.all()
    best_match = None
    best_distance = float("inf")

    for temp in temps:
        dist = cosine(embedding, np.array(temp.face_embedding))
        if dist < best_distance:
            best_distance = dist
            best_match = temp

    if best_match and best_distance < TEMP_THRESHOLD:
        best_match.appearances += 1
        best_match.save()
        return best_match, False

    # Create only ONCE
    username = f"visitor_{get_random_string(8)}"
    email = f"{username}@mispartechnologies.com"

    temp_user = TempUser.objects.create(
        temp_username=username,
        temp_email=email,
        face_embedding=embedding.tolist(),
        appearances=1,
    )

    return temp_user, True

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