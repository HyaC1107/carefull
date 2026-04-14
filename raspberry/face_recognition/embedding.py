from raspberry.config.settings import MODEL_PATH
from raspberry.face_recognition.model_loader import FaceModel

model = FaceModel(MODEL_PATH)


def get_embedding(face_img):
    if face_img is None or face_img.size == 0:
        raise ValueError("face image is empty")

    return model.predict(face_img)
