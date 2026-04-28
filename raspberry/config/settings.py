import os
from dotenv import load_dotenv
from utils.device_id import get_device_uid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_DIR = os.path.join(BASE_DIR, "db")
MODELS_DIR = os.path.join(BASE_DIR, "models")
ENV_DIR = os.path.join(BASE_DIR, ".env")

MODEL_PATH = os.path.join(MODELS_DIR, "mobilefacenet.tflite")
CAMERA_WIDTH = int(os.getenv("CAREFULL_CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.getenv("CAREFULL_CAMERA_HEIGHT", "480"))
CAMERA_WARMUP_SECONDS = float(os.getenv("CAREFULL_CAMERA_WARMUP_SECONDS", "2"))
SCHEDULE_POLL_SECONDS = int(os.getenv("CAREFULL_SCHEDULE_POLL_SECONDS", "30"))
AUTH_RETRY_COUNT = int(os.getenv("CAREFULL_AUTH_RETRY_COUNT", "5"))
AUTH_RETRY_DELAY_SECONDS = float(os.getenv("CAREFULL_AUTH_RETRY_DELAY_SECONDS", "1"))
FACE_MATCH_THRESHOLD = float(os.getenv("CAREFULL_FACE_MATCH_THRESHOLD", "0.8"))

SCREEN_WIDTH = int(os.getenv("CAREFULL_SCREEN_WIDTH", "1280"))
SCREEN_HEIGHT = int(os.getenv("CAREFULL_SCREEN_HEIGHT", "600"))

USE_WEBCAM    = os.getenv("CAREFULL_USE_WEBCAM",    "0") == "1"
UI_TEST_MODE  = os.getenv("CAREFULL_UI_TEST_MODE", "0") == "1"
FULLSCREEN    = os.getenv("CAREFULL_FULLSCREEN",   "1") == "1"

# API
API_BASE_URL = os.getenv("CAREFULL_API_BASE_URL", "http://localhost:3000")
DEVICE_UID   = get_device_uid()
API_TIMEOUT  = int(os.getenv("CAREFULL_API_TIMEOUT", "10"))

# Voice & TTS Settings
VOICES_DIR = os.path.join(BASE_DIR, "voices")
TTS_LANG = os.getenv("CAREFULL_TTS_LANG", "ko")
TTS_FILE_PATH = os.path.join(VOICES_DIR, "default_alarm.mp3")
# UI 폰트 크기 (pt) — 고령자 대상, 여기서만 수정하면 전체 반영
FONT_TITLE  = 50   # 화면 메인 타이틀
FONT_HEAD   = 42   # 섹션 헤딩 / 인증 타이틀
FONT_BODY   = 30   # 본문 / 설명 텍스트
FONT_SMALL  = 24   # 보조 텍스트, 카운터
FONT_BUTTON = 28   # 버튼 텍스트
