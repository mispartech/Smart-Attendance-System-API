import base64, cv2, json, numpy as np

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from attendanceapi.services.face_recognition_service import recognize_faces_from_frame


@api_view(["POST"])
def recognize_frame(request):
    """
    Receives a base64-encoded image and returns face recognition results.
    """

    data = request.data

    # Handle raw string payloads
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
        # Remove data URL prefix if present
        if "," in frame_data:
            frame_data = frame_data.split(",")[1]

        frame_bytes = base64.b64decode(frame_data)
        np_arr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return Response(
                {"error": "Invalid image data"},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = recognize_faces_from_frame(frame)

        return Response(
            {
                "faces": results,
                "count": len(results)
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
