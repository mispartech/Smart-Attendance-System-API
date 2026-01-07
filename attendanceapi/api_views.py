import base64, cv2, json, numpy as np, pytz
from django.utils.timezone import now
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from attendanceapi.models import Attendance, FaceEmbedding
from attendanceapi.services.face_recognition_service import (
    extract_face_embedding,
    recognize_face,
    match_or_create_temp_user,
    recognize_faces_from_frame
)
from base.models import Department


@api_view(["POST"])
def recognize_frame(request):
    """
    Accepts a base64 image frame and returns:
    - Registered user if matched
    - Temporary user if not matched
    """

    frame_data = request.data.get("frame")

    if not frame_data:
        return Response(
            {"error": "frame is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 🔹 Step 1: extract embedding
        embedding = extract_face_embedding(frame_data)

        if embedding is None:
            return Response(
                {"error": "No face detected"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔹 Step 2: try registered users
        user = recognize_face(embedding)

        if user:
            return Response({
                "status": "recognized",
                "user_type": "registered",
                "user_id": user.id,
                "full_name": user.get_full_name(),
            }, status=status.HTTP_200_OK)

        # 🔹 Step 3: temp user fallback
        temp_user, created = match_or_create_temp_user(embedding)

        return Response({
            "status": "recognized",
            "user_type": "temporary",
            "temp_user_id": temp_user.id,
            "created": created,
            "appearances": temp_user.appearances,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # 🔥 NEVER silently fail
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
def mark_attendance(request):
    """
    Recognize faces and mark attendance.
    Mirrors process_frame_logic without rendering or streaming.
    """

    data = request.data

    if isinstance(data, str):
        frame_data = data
    else:
        frame_data = data.get("frame")

    if not frame_data:
        return Response(
            {"error": "No frame data provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        if "," in frame_data:
            frame_data = frame_data.split(",")[1]

        frame_bytes = base64.b64decode(frame_data)
        frame = cv2.imdecode(
            np.frombuffer(frame_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )

        if frame is None:
            return Response(
                {"error": "Invalid image data"},
                status=status.HTTP_400_BAD_REQUEST
            )

        faces = recognize_faces_from_frame(frame)

        if not faces:
            return Response(
                {"message": "No faces detected"},
                status=status.HTTP_200_OK
            )

        lagos_tz = pytz.timezone("Africa/Lagos")
        now_local = now().astimezone(lagos_tz)
        today = now_local.date()

        marked = []

        with transaction.atomic():
            for face in faces:
                if not face["recognized"]:
                    temp_user, created = match_or_create_temp_user(face["embedding"])

                    TempAttendance.objects.get_or_create(
                        temp_user=temp_user,
                        date=today
                    )

                    marked.append({
                        "visitor_id": str(temp_user.id),
                        "recognized": False,
                        "new": created
                    })
                    continue

                user_id = face["user_id"]
                confidence = face["confidence"]

                embedding = FaceEmbedding.objects.select_related("user").filter(
                    user_id=user_id
                ).first()

                if not embedding:
                    continue

                user = embedding.user

                attendance, created = Attendance.objects.get_or_create(
                    member=user,
                    date=today,
                    defaults={
                        "face_detections": 1,
                        "time": now_local.time(),
                        "distance": 1 - confidence,
                        "gender": user.gender,
                        "role": user.role,
                        "department": user.department,
                        "recognized_emotion": "Neutral",
                    }
                )

                if not created:
                    attendance.face_detections += 1
                    attendance.save()

                marked.append({
                    "user_id": str(user.id),
                    "name": f"{user.first_name} {user.last_name}",
                    "confidence": confidence,
                    "new": created
                })

        return Response(
            {
                "marked": marked,
                "count": len(marked)
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
