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
    Marks attendance using a face frame.
    Immutable attendance record.
    """

    frame_data = request.data.get("frame")

    if not frame_data:
        return Response(
            {"error": "frame is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 1️⃣ Face embedding
        embedding = extract_face_embedding(frame_data)

        if embedding is None:
            return Response(
                {"error": "No face detected"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2️⃣ Registered user
        user = recognize_face(embedding)

        if user:
            attendance = Attendance.objects.create(
                user=user,
                timestamp=timezone.now()
            )

            return Response({
                "status": "success",
                "user_type": "registered",
                "user_id": user.id,
                "attendance_id": attendance.id,
                "timestamp": attendance.timestamp
            }, status=status.HTTP_201_CREATED)

        # 3️⃣ Temporary user
        temp_user, created = match_or_create_temp_user(embedding)

        attendance = Attendance.objects.create(
            temp_user=temp_user,
            timestamp=timezone.now()
        )

        return Response({
            "status": "success",
            "user_type": "temporary",
            "temp_user_id": temp_user.id,
            "attendance_id": attendance.id,
            "timestamp": attendance.timestamp,
            "created": created
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
