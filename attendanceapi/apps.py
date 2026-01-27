from django.apps import AppConfig

class AttendanceapiConfig(AppConfig):
    name = "attendanceapi"

    def ready(self):
        from attendanceapi.services.face_model import get_face_app
        get_face_app()
        print("Face model initialized and ready.")