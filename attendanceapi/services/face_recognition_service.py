import numpy as np
from django.utils import timezone

from attendanceapi.models import FaceEmbedding
from attendanceapi.utils import get_face_app, cosine_distance


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
            distance = cosine_distance(
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
