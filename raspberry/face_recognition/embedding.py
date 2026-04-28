from face_recognition.model_loader import get_model


def get_embedding(face_img):
    if face_img is None or face_img.size == 0:
        raise ValueError("face image is empty")
    model = get_model()
    if model is None:
        raise RuntimeError("얼굴 인식 모델 미로드 상태")
    return model.predict(face_img)
