import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

CLAUDE_MODEL = "claude-sonnet-4-5"

IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "huggingface")
HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
LOCAL_SD_URL = "http://127.0.0.1:7860"

VIDEO_MODE = os.getenv("VIDEO_MODE", "slideshow")
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
IMAGE_DURATION_SEC = 3.0

TTS_VOICE = "ko-KR-SunHiNeural"
OUTPUT_DIR = "outputs"
