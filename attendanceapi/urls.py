from django.urls import path
from attendanceapi.api_views import recognize_frame, mark_attendance, health_check
from attendanceapi.api_views import api_version

urlpatterns = [
    path("recognize-frame/", recognize_frame, name="recognize-frame"),
    path("attendance/mark/", mark_attendance, name="mark-attendance"),
    path("health/", health_check, name="health"),
    path("version/", api_version, name="version"),
]
