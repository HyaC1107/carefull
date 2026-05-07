import cv2
import numpy as np

from config.settings import MODEL_PATH


def _load_interpreter(model_path: str):
    """tflite_runtime → tensorflow.lite 순서로 폴백."""
    try:
        from tflite_runtime.interpreter import Interpreter
        return Interpreter(model_path=model_path)
    except ImportError:
        pass
    try:
        import tensorflow as tf
        return tf.lite.Interpreter(model_path=model_path)
    except ImportError:
        pass
    raise RuntimeError("tflite_runtime 또는 tensorflow 중 하나가 필요합니다.")


class FaceModel:
    def __init__(self, model_path: str = MODEL_PATH):
        import os
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"모델 파일 없음: {model_path}")

        self.interpreter = _load_interpreter(model_path)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_shape = self.input_details[0]["shape"]
        self.input_dtype = self.input_details[0]["dtype"]

    def preprocess(self, face_img):
        face_img = cv2.resize(face_img, (self.input_shape[2], self.input_shape[1]))
        face_img = face_img.astype(np.float32)
        face_img = (face_img - 127.5) / 128.0
        return np.expand_dims(face_img, axis=0)

    def predict(self, face_img):
        input_data = self.preprocess(face_img)

        if self.input_dtype == np.uint8:
            scale, zero_point = self.input_details[0]["quantization"]
            if scale > 0:
                input_data = input_data / scale + zero_point
            input_data = input_data.astype(np.uint8)

        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()

        output = self.interpreter.get_tensor(self.output_details[0]["index"])[0].copy()
        norm = np.linalg.norm(output)
        return output / norm if norm > 0 else output


# 싱글턴 — 최초 호출 시 로드, 모델 없으면 None
_model: FaceModel | None = None
_model_loaded = False


def get_model() -> FaceModel | None:
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    try:
        _model = FaceModel()
    except Exception as e:
        print(f"[MODEL] 로드 실패 (얼굴인식 비활성화): {e}")
        _model = None
    return _model
