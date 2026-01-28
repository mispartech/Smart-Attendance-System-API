from django.conf import settings
import base64, cv2, json, numpy as np, pytz, re
from django.utils.timezone import now
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from attendanceapi.models import Attendance, FaceEmbedding, TempUser
from attendanceapi.services.face_recognition_service import (
    extract_face_embedding,
    recognize_face,
    match_or_create_temp_user,
    recognize_faces_from_frame,
)
from attendanceapi.services.attendance_service import has_recent_attendance
from base.models import Department
from attendanceapi.services.face_model import get_face_app
from attendanceapi.services.image_utils import decode_base64_image

BASE64_IMAGE_REGEX = re.compile(
    r"^[A-Za-z0-9+/=]+$"
)

@api_view(["POST"])
def recognize_frame(request):
    """
    Accepts a base64 image frame and returns detected faces with bbox + identity.
    """

    frame_data = request.data.get("frame")

    if not frame_data:
        return Response({
            "status": "error",
            "code": "FRAME_MISSING",
            "message": "Frame field is required",
            "data": {}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. Strip base64 header
        if "," in frame_data:
            frame_data = frame_data.split(",")[1]

        # 2. Decode base64
        image_bytes = base64.b64decode(frame_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0:
            return Response({
                "status": "error",
                "code": "INVALID_IMAGE",
                "message": "Invalid image",
                "data": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. Detect & recognize faces (MULTI-FACE)
        results = recognize_faces_from_frame(frame)

        faces = []

        for result in results:
            if result.get("recognized"):
                user = result["user"]
                faces.append({
                    "recognized": True,
                    "user_type": "registered",
                    "user_id": str(user.id),
                    "name": user.get_full_name() or user.username,
                    "bbox": result["bbox"],
                })
            else:
                faces.append({
                    "recognized": False,
                    "user_type": "unknown",
                    "bbox": result["bbox"],
                })

        return Response({
            "status": "success",
            "code": "FACES_DETECTED" if faces else "NO_FACE",
            "message": "Faces processed",
            "data": {"faces": faces}
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print("🔥 recognize_frame error:", str(e))
        return Response({
            "status": "error",
            "code": "RECOGNITION_FAILED",
            "message": "Internal recognition error",
            "data": {}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def mark_attendance(request):
    frame_data = request.data.get("frame")

    if not frame_data:
        return Response({
            "status": "error",
            "code": "FRAME_MISSING",
            "message": "Frame field is required",
            "data": {}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # -------------------------------
        # 1️⃣ Decode image
        # -------------------------------
        frame = decode_base64_image(frame_data)

        if frame is None:
            return Response({
                "status": "error",
                "code": "INVALID_IMAGE",
                "message": "Invalid or corrupted image",
                "data": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        # -------------------------------
        # 2️⃣ Extract face embedding
        # -------------------------------
        embedding = extract_face_embedding(frame)

        if embedding is None:
            return Response({
                "status": "success",
                "code": "NO_FACE",
                "message": "No face detected in frame",
                "data": {}
            }, status=status.HTTP_200_OK)

        # -------------------------------
        # 3️⃣ Try registered user
        # -------------------------------
        user = recognize_face(embedding)

        if user:
            if has_recent_attendance(user=user):
                return Response({
                    "status": "duplicate",
                    "code": "ATTENDANCE_DUPLICATE",
                    "message": "Attendance already marked recently",
                    "data": {}
                }, status=status.HTTP_200_OK)

            attendance = Attendance.objects.create(
                user=user,
                timestamp=timezone.now()
            )

            return Response({
                "status": "success",
                "code": "ATTENDANCE_MARKED",
                "message": "Attendance recorded successfully",
                "data": {
                    "attendance_id": attendance.id,
                    "user_id": user.id
                }
            }, status=status.HTTP_201_CREATED)

        # -------------------------------
        # 4️⃣ Temporary user fallback
        # -------------------------------
        temp_user, created = match_or_create_temp_user(embedding)

        if has_recent_attendance(temp_user=temp_user):
            return Response({
                "status": "duplicate",
                "code": "TEMP_ATTENDANCE_DUPLICATE",
                "message": "Temporary attendance already marked recently",
                "data": {}
            }, status=status.HTTP_200_OK)

        attendance = Attendance.objects.create(
            temp_user=temp_user,
            timestamp=timezone.now()
        )

        return Response({
            "status": "success",
            "code": "TEMP_ATTENDANCE_MARKED",
            "message": "Temporary attendance recorded",
            "data": {
                "temp_user_id": temp_user.id,
                "created": created
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            "status": "error",
            "code": "ATTENDANCE_FAILED",
            "message": "Internal attendance error",
            "debug": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def health_check(request):
    return Response({
        "status": "success",
        "code": "API_HEALTHY",
        "message": "Attendance API is running",
        "data": {}
    })

@api_view(["GET"])
def api_version(request):
    return Response({
        "status": "success",
        "code": "API_VERSION",
        "message": "API version retrieved",
        "data": {
            "name": "Smart Attendance System API",
            "version": "1.0.0",
        }
    })
