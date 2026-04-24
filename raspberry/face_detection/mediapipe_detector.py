import cv2
import mediapipe as mp

mp_face_detection = mp.solutions.face_detection
face_detection = mp_face_detection.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.5,
)


def detect_face(image):
    if image is None:
        return []

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb_image)
    faces = []

    if results.detections:
        h, w, _ = image.shape

        for detection in results.detections:
            bbox = detection.location_data.relative_bounding_box
            x = max(0, int(bbox.xmin * w))
            y = max(0, int(bbox.ymin * h))
            width = min(int(bbox.width * w), w - x)
            height = min(int(bbox.height * h), h - y)

            if width > 0 and height > 0:
                faces.append((x, y, width, height))

    return faces
