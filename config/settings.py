import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "db")
TESTS_DIR = os.path.join(BASE_DIR, "tests")
MODELS_DIR = os.path.join(BASE_DIR, "models")

TEST_MODE = os.getenv("CAREFULL_TEST_MODE", "1") == "1"
TEST_IMAGE_PATH = os.getenv(
    "CAREFULL_TEST_IMAGE",
    os.path.join(TESTS_DIR, "test.jpg"),
)
SCHEDULE_POLL_SECONDS = int(os.getenv("CAREFULL_SCHEDULE_POLL_SECONDS", "30"))
FACE_MATCH_THRESHOLD = float(os.getenv("CAREFULL_FACE_MATCH_THRESHOLD", "0.8"))
