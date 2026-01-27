import base64
import cv2
import numpy as np

def decode_base64_image(frame_data: str):
    if not frame_data:
        return None

    if "," in frame_data:
        frame_data = frame_data.split(",")[1]

    image_bytes = base64.b64decode(frame_data, validate=True)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    return frame