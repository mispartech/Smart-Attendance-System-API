from django.urls import path
from attendanceapi.api_views import recognize_frame

urlpatterns = [
    path("recognize-frame/", recognize_frame, name="recognize-frame"),
]
