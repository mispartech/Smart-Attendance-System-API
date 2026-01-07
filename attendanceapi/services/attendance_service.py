from django.utils import timezone
from datetime import timedelta
from attendanceapi.models import Attendance


ATTENDANCE_COOLDOWN_MINUTES = 5


def has_recent_attendance(user=None, temp_user=None):
    """
    Prevent duplicate attendance within cooldown window
    """
    now = timezone.now()
    window_start = now - timedelta(minutes=ATTENDANCE_COOLDOWN_MINUTES)

    filters = {"timestamp__gte": window_start}

    if user:
        filters["user"] = user
    if temp_user:
        filters["temp_user"] = temp_user

    return Attendance.objects.filter(**filters).exists()
