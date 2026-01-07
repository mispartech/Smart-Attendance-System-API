from datetime import timedelta, time
from django.db.models import Q
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from .models import Attendance, TempAttendance

FACE_APP = None

def get_face_app():
    global FACE_APP
    if FACE_APP is None:
        FACE_APP = FaceAnalysis(
            name='buffalo_s',
            providers=['CPUExecutionProvider'],
            allowed_modules=['detection', 'recognition']
        )
        FACE_APP.prepare(ctx_id=0, det_size=(640, 640))
    return FACE_APP

def get_filtered_attendance_queryset(request):
    queryset = Attendance.objects.select_related('member')

    # Get params
    date = request.GET.get("date")
    time_value = request.GET.get("time")
    name = request.GET.get("name")
    role = request.GET.get("role")
    sort = request.GET.get("sort")


    # ------------------------------------
    # 1️⃣ DATE FILTER
    # ------------------------------------
    parsed_date = None
    if date:
        parsed_date = parse_date(date)
        queryset = queryset.filter(date=parsed_date)

    # ------------------------------------
    # 2️⃣ TIME FILTER (HH:MM, ignore seconds)
    # ------------------------------------
    if time_value:
        hour, minute = map(int, time_value.split(":"))
        start_time = time(hour, minute, 0)
        end_time = time(hour, minute, 59)

        # If a DATE was selected, filter by date + time range
        if parsed_date:
            queryset = queryset.filter(
                date=parsed_date,
                time__range=(start_time, end_time)
            )
        else:
            # IF NO DATE SELECTED → Search all dates by time only
            queryset = queryset.filter(
                time__range=(start_time, end_time)
            )

    # ------------------------------------
    # 3️⃣ NAME FILTER
    # ------------------------------------
    if name:
        queryset = queryset.filter(
            Q(member__first_name__icontains=name) |
            Q(member__last_name__icontains=name)
        )

    # ------------------------------------
    # 4️⃣ ROLE FILTER
    # ------------------------------------
    if role:
        queryset = queryset.filter(role=role)

    # ------------------------------------
    # 5️⃣ SORTING
    # ------------------------------------
    if sort == 'recent':
        queryset = queryset.order_by('-date', '-time')
    elif sort == 'asc':
        queryset = queryset.order_by('date', 'time')
    elif sort == 'desc':
        queryset = queryset.order_by('-date', '-time')
    elif sort == 'last_7_days':
        queryset = queryset.filter(date__gte=now().date() - timedelta(days=7))
    elif sort == 'last_month':
        today = now().date()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        queryset = queryset.filter(date__range=(first_day_last_month, last_day_last_month))

    # FINAL SQL OUTPUT
    return queryset


def base_attendance_filter(request, queryset):
    """Applies date, time, name, role, and sorting filters to any queryset."""

    date = request.GET.get("date")
    time_value = request.GET.get("time")
    name = request.GET.get("name")
    role = request.GET.get("role")
    sort = request.GET.get("sort")

    parsed_date = None
    if date:
        parsed_date = parse_date(date)
        if parsed_date:
            queryset = queryset.filter(date=parsed_date)

    # TIME filter (HH:MM → ignore seconds)
    if time_value:
        hour, minute = map(int, time_value.split(":"))
        start_t = time(hour, minute, 0)
        end_t = time(hour, minute, 59)

        if parsed_date:
            queryset = queryset.filter(date=parsed_date, time__range=(start_t, end_t))
        else:
            queryset = queryset.filter(time__range=(start_t, end_t))

    # NAME filter
    if name:
        queryset = queryset.filter(
            Q(member__first_name__icontains=name) |
            Q(member__last_name__icontains=name)
        )

    # ROLE filter (only applies to Attendance queryset, not TempAttendance)
    if role and hasattr(queryset.model, "role"):
        queryset = queryset.filter(role=role)

    # SORTING
    if sort == 'recent':
        queryset = queryset.order_by('-date', '-time')
    elif sort == 'asc':
        queryset = queryset.order_by('date', 'time')
    elif sort == 'desc':
        queryset = queryset.order_by('-date', '-time')
    elif sort == 'last_7_days':
        queryset = queryset.filter(date__gte=now().date() - timedelta(days=7))
    elif sort == 'last_month':
        today = now().date()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        queryset = queryset.filter(date__range=(first_day_last_month, last_day_last_month))

    return queryset


# -------------------------------
#   1️⃣ MEMBERS ATTENDANCE
# -------------------------------
def get_members_attendance(request):
    queryset = Attendance.objects.select_related("member").filter(role="member")
    return base_attendance_filter(request, queryset)


# -------------------------------
#   2️⃣ WORKERS ATTENDANCE
# -------------------------------
def get_workers_attendance(request):
    queryset = Attendance.objects.select_related("member").exclude(role="member")
    return base_attendance_filter(request, queryset)


# -------------------------------
#   3️⃣ TEMPORARY (VISITORS)
# -------------------------------
def get_temp_attendance(request):
    queryset = TempAttendance.objects.select_related("temp_user")
    return base_attendance_filter(request, queryset)
