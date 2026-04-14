import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "db")
MODELS_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(MODELS_DIR, "mobilefacenet.tflite")
CAMERA_WIDTH = int(os.getenv("CAREFULL_CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.getenv("CAREFULL_CAMERA_HEIGHT", "480"))
CAMERA_WARMUP_SECONDS = float(os.getenv("CAREFULL_CAMERA_WARMUP_SECONDS", "2"))
SCHEDULE_POLL_SECONDS = int(os.getenv("CAREFULL_SCHEDULE_POLL_SECONDS", "30"))
AUTH_RETRY_COUNT = int(os.getenv("CAREFULL_AUTH_RETRY_COUNT", "5"))
AUTH_RETRY_DELAY_SECONDS = float(os.getenv("CAREFULL_AUTH_RETRY_DELAY_SECONDS", "1"))
FACE_MATCH_THRESHOLD = float(os.getenv("CAREFULL_FACE_MATCH_THRESHOLD", "0.8"))
