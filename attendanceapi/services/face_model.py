from insightface.app import FaceAnalysis

_face_app = None

def get_face_app():
    global _face_app

    if _face_app is None:
        _face_app = FaceAnalysis(name="buffalo_s")
        _face_app.prepare(ctx_id=0)

    return _face_app
