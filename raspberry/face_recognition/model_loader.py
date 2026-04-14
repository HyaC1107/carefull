import cv2
import numpy as np
from tflite_runtime.interpreter import Interpreter


class FaceModel:
    def __init__(self, model_path):
        self.interpreter = Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.input_shape = self.input_details[0]["shape"]
        self.input_dtype = self.input_details[0]["dtype"]

    def preprocess(self, face_img):
        face_img = cv2.resize(face_img, (self.input_shape[2], self.input_shape[1]))
        face_img = face_img.astype(np.float32)
        face_img = (face_img - 127.5) / 128.0
        face_img = np.expand_dims(face_img, axis=0)
        return face_img

    def predict(self, face_img):
        input_data = self.preprocess(face_img)

        if self.input_dtype == np.uint8:
            scale, zero_point = self.input_details[0]["quantization"]
            if scale > 0:
                input_data = input_data / scale + zero_point
            input_data = input_data.astype(np.uint8)

        self.interpreter.set_tensor(self.input_details[0]["index"], input_data)
        self.interpreter.invoke()

        output = self.interpreter.get_tensor(self.output_details[0]["index"])[0]
        norm = np.linalg.norm(output)
        if norm > 0:
            output = output / norm

        return output
