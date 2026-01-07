from django.urls import path
from attendanceapi.api_views import recognize_frame, mark_attendance

urlpatterns = [
    path("recognize-frame/", recognize_frame, name="recognize-frame"),
    path("recognize-frame/", recognize_frame),
    path("attendance/mark/", mark_attendance),
]
