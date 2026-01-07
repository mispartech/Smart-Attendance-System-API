from django.urls import path
from attendanceapi.api_views import recognize_frame, mark_attendance, health_check

urlpatterns = [
    path("recognize-frame/", recognize_frame, name="recognize-frame"),
    path("recognize-frame/", recognize_frame),
    path("attendance/mark/", mark_attendance),
    path("health/", health_check),
    path("version/", api_version),
]
