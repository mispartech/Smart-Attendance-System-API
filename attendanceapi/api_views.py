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
    Accepts a base64 image frame and returns:
    - Registered user if matched
    - Temporary user if not matched
    Provides explicit debug info for every failure point.
    """

    print("RAW request.data:", request.data)
    print("Keys:", request.data.keys())

    frame_data = request.data.get("frame")

    if not frame_data:
        print("⚠️ Frame missing in request")
        return Response({
            "status": "error",
            "code": "FRAME_MISSING",
            "message": "Frame field is required",
            "data": {}
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # -------------------------------
        # 1. Clean base64 header if exists
        # -------------------------------
        if "," in frame_data:
            frame_data = frame_data.split(",")[1]

        # -------------------------------
        # 2. Decode base64 safely
        # -------------------------------
        try:
            image_bytes = base64.b64decode(frame_data, validate=True)
        except Exception as e:
            print(f"⚠️ Invalid base64 encoding: {e}")
            return Response({
                "status": "error",
                "code": "INVALID_BASE64",
                "message": "Invalid base64 image encoding",
                "debug": str(e) if settings.DEBUG else None,
                "data": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        # -------------------------------
        # 3. Convert to OpenCV image
        # -------------------------------
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None or frame.size == 0:
            print("⚠️ Decoded frame is invalid or empty")
            return Response({
                "status": "error",
                "code": "INVALID_IMAGE",
                "message": "Decoded image is invalid or corrupted",
                "data": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        # -------------------------------
        # 4. Extract face embedding
        # -------------------------------
        try:
            embedding = extract_face_embedding(frame)
        except Exception as e:
            print(f"⚠️ Error extracting face embedding: {e}")
            return Response({
                "status": "error",
                "code": "EMBEDDING_EXTRACTION_FAILED",
                "message": "Failed to extract face embedding",
                "debug": str(e) if settings.DEBUG else None,
                "data": {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if embedding is None:
            print("⚠️ No face detected or embedding is None")
            return Response({
                "status": "success",
                "code": "NO_FACE",
                "message": "No face detected in frame",
                "data": {"faces": []}
            }, status=status.HTTP_200_OK)

        # -------------------------------
        # 5. Recognize registered user
        # -------------------------------
        try:
            user = recognize_face(embedding)
        except Exception as e:
            print(f"⚠️ Error recognizing registered user: {e}")
            user = None

        if user:
            print(f"✅ Registered user recognized: {user}")
            return Response({
                "status": "success",
                "code": "FACE_RECOGNIZED",
                "message": "Registered user recognized",
                "data": {
                    "faces": [{
                        "recognized": True,
                        "user_type": "registered",
                        "user_id": str(user.id),
                        "name": user.get_full_name() if hasattr(user, "get_full_name") else str(user),
                    }]
                }
            }, status=status.HTTP_200_OK)

        # -------------------------------
        # 6. Temporary user fallback
        # -------------------------------
        try:
            temp_user, created = match_or_create_temp_user(embedding)
            print(f"ℹ️ Temporary user {'created' if created else 'matched'}: {temp_user.temp_username}")
        except Exception as e:
            print(f"⚠️ Error creating/matching temp user: {e}")
            return Response({
                "status": "error",
                "code": "TEMP_USER_FAILED",
                "message": "Failed to match or create temporary user",
                "debug": str(e) if settings.DEBUG else None,
                "data": {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "status": "success",
            "code": "TEMP_USER",
            "message": "Temporary user identified",
            "data": {
                "faces": [{
                    "recognized": False,
                    "user_type": "temporary",
                    "temp_user_id": str(temp_user.id),
                    "created": created,
                    "appearances": temp_user.appearances,
                }]
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print("🔥 Unexpected error in recognize_frame:", str(e))
        return Response({
            "status": "error",
            "code": "RECOGNITION_FAILED",
            "message": "Internal recognition error",
            "debug": str(e) if settings.DEBUG else "Internal error",
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
