"""Cấu hình đọc từ file .env ở thư mục gốc."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _get("CLAUDE_MODEL", "claude-sonnet-4-5")

ARK_API_KEY = _get("ARK_API_KEY")
ARK_BASE_URL = _get("ARK_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3").rstrip("/")
SEEDANCE_MODEL = _get("SEEDANCE_MODEL", "dreamina-seedance-2-0-260128")
DEMO_RESOLUTION = _get("DEMO_RESOLUTION", "480p")
VIDEO_RATIO = _get("VIDEO_RATIO", "9:16")
SEEDANCE_MIN_DURATION = int(_get("SEEDANCE_MIN_DURATION", "4"))
SEEDANCE_MAX_DURATION = int(_get("SEEDANCE_MAX_DURATION", "15"))
SEEDANCE_SEND_SEED = _get("SEEDANCE_SEND_SEED", "0") == "1"
MAX_PARALLEL_RENDERS = int(_get("MAX_PARALLEL_RENDERS", "3"))

MOCK_CLAUDE = _get("MOCK_CLAUDE", "auto")
MOCK_SEEDANCE = _get("MOCK_SEEDANCE", "auto")

FFMPEG_BIN = _get("FFMPEG_BIN", "ffmpeg")
DEMO_W, DEMO_H = (int(x) for x in _get("DEMO_SIZE", "360x640").lower().split("x"))
DEMO_FPS = int(_get("DEMO_FPS", "24"))

DATA_DIR = Path(_get("DATA_DIR") or (ROOT / "data" / "projects"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def use_mock_claude() -> bool:
    return MOCK_CLAUDE == "1" or (MOCK_CLAUDE == "auto" and not ANTHROPIC_API_KEY)


def use_mock_seedance() -> bool:
    return MOCK_SEEDANCE == "1" or (MOCK_SEEDANCE == "auto" and not ARK_API_KEY)
