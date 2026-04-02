import cv2
import numpy as np
import tensorflow as tf


class FaceModel:
    def __init__(self, model_path):
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def predict(self, face_img):
        input_shape = self.input_details[0]["shape"]
        face_img = cv2.resize(face_img, (input_shape[2], input_shape[1]))
        face_img = face_img.astype(np.float32) / 255.0
        face_img = np.expand_dims(face_img, axis=0)

        self.interpreter.set_tensor(self.input_details[0]["index"], face_img)
        self.interpreter.invoke()

        output = self.interpreter.get_tensor(self.output_details[0]["index"])
        return output[0]
