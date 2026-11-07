"""Cấu hình đọc từ file .env ở thư mục gốc (hoặc biến môi trường khi chạy Docker)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _get(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _bool(name: str, default: str = "0") -> bool:
    return _get(name, default).lower() in ("1", "true", "yes", "on")


def _list(name: str, default: str = "") -> list:
    return [x.strip() for x in _get(name, default).split(",") if x.strip()]


# ================= Web =================
HOST = _get("HOST", "127.0.0.1")
PORT = int(_get("PORT", "8000"))
WEB_USER = _get("WEB_USER")              # bật đăng nhập Basic Auth khi deploy lên VPS
WEB_PASSWORD = _get("WEB_PASSWORD")

# ================= Claude (LLM cho mọi agent) =================
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _get("CLAUDE_MODEL", "claude-sonnet-4-5")
CLAUDE_MODEL_FAST = _get("CLAUDE_MODEL_FAST") or CLAUDE_MODEL   # agent phụ: critic, SEO, QA
CRITIC_ENABLED = _bool("CRITIC_ENABLED", "1")
CRITIC_MIN_SCORE = int(_get("CRITIC_MIN_SCORE", "7"))
CRITIC_MAX_ROUNDS = int(_get("CRITIC_MAX_ROUNDS", "2"))

# ================= Video AI: Seedance (BytePlus ModelArk) =================
ARK_API_KEY = _get("ARK_API_KEY")
ARK_BASE_URL = _get("ARK_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3").rstrip("/")
SEEDANCE_MODEL = _get("SEEDANCE_MODEL", "dreamina-seedance-2-0-260128")
SEEDANCE_MIN_DURATION = int(_get("SEEDANCE_MIN_DURATION", "4"))
SEEDANCE_MAX_DURATION = int(_get("SEEDANCE_MAX_DURATION", "15"))
SEEDANCE_SEND_SEED = _bool("SEEDANCE_SEND_SEED", "0")

# ================= Video/ảnh AI: fal.ai (Kling, Wan, Veo, Flux...) =================
FAL_KEY = _get("FAL_KEY")
FAL_VIDEO_MODEL = _get("FAL_VIDEO_MODEL", "fal-ai/kling-video/v2.1/standard/text-to-video")
FAL_VIDEO_EXTRA = _get("FAL_VIDEO_EXTRA", "")   # JSON tham số bổ sung tuỳ model
FAL_IMAGE_MODEL = _get("FAL_IMAGE_MODEL", "fal-ai/flux/schnell")

# Nhà cung cấp video AI chính: seedance | fal
VIDEO_PROVIDER = _get("VIDEO_PROVIDER", "seedance")
# Định tuyến nguồn hình: auto (đạo diễn chọn theo cảnh) | ai_video | ai_image | stock
VISUAL_MODE = _get("VISUAL_MODE", "auto")

# ================= Stock footage =================
PEXELS_API_KEY = _get("PEXELS_API_KEY")

# ================= Lời thoại (TTS) =================
# edge (miễn phí) | elevenlabs | fpt | none
TTS_PROVIDER = _get("TTS_PROVIDER", "edge")
EDGE_VOICE = _get("EDGE_VOICE", "vi-VN-HoaiMyNeural")     # nam: vi-VN-NamMinhNeural
EDGE_RATE = _get("EDGE_RATE", "+8%")
ELEVENLABS_API_KEY = _get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _get("ELEVENLABS_VOICE_ID")
ELEVENLABS_MODEL = _get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
FPT_API_KEY = _get("FPT_API_KEY")
FPT_VOICE = _get("FPT_VOICE", "banmai")

# ================= Nhạc nền, logo =================
ASSETS_DIR = Path(_get("ASSETS_DIR") or (ROOT / "assets"))
MUSIC_DIR = ASSETS_DIR / "music"
LOGO_FILE = ASSETS_DIR / "logo.png"
MUSIC_VOLUME = float(_get("MUSIC_VOLUME", "0.18"))

# ================= Dựng video =================
FFMPEG_BIN = _get("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = _get("FFPROBE_BIN", "ffprobe")
DEFAULT_RESOLUTION = _get("DEFAULT_RESOLUTION") or _get("DEMO_RESOLUTION", "720p")
RESOLUTION_OPTIONS = _list("RESOLUTION_OPTIONS", "480p,720p,1080p")
VIDEO_RATIO = _get("VIDEO_RATIO", "9:16")
FPS = int(_get("FPS", "30"))
SUB_FONT = _get("SUB_FONT", "Arial")              # Docker/Linux: "DejaVu Sans"
SUB_WORDS_PER_LINE = int(_get("SUB_WORDS_PER_LINE", "4"))
THUMB_FONT = _get("THUMB_FONT", "")               # đường dẫn .ttf, trống = tự tìm
TARGET_LUFS = float(_get("TARGET_LUFS", "-14"))
VOICE_PADDING = float(_get("VOICE_PADDING", "0.35"))   # giây nghỉ sau mỗi câu thoại

# ================= QA =================
QA_VISION = _bool("QA_VISION", "1")

# ================= Đăng bài =================
PUBLISH_DRY_RUN = _bool("PUBLISH_DRY_RUN", "1")   # 1 = chỉ giả lập, không đăng thật
SECRETS_DIR = Path(_get("SECRETS_DIR") or (ROOT / "data" / "secrets"))
YOUTUBE_CLIENT_SECRET = Path(_get("YOUTUBE_CLIENT_SECRET") or (SECRETS_DIR / "youtube_client_secret.json"))
YOUTUBE_TOKEN = SECRETS_DIR / "youtube_token.json"
YOUTUBE_PRIVACY = _get("YOUTUBE_PRIVACY", "private")          # private | unlisted | public
YOUTUBE_CATEGORY_ID = _get("YOUTUBE_CATEGORY_ID", "22")
TIKTOK_CLIENT_KEY = _get("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = _get("TIKTOK_CLIENT_SECRET")
TIKTOK_ACCESS_TOKEN = _get("TIKTOK_ACCESS_TOKEN")
TIKTOK_REFRESH_TOKEN = _get("TIKTOK_REFRESH_TOKEN")
TIKTOK_PRIVACY = _get("TIKTOK_PRIVACY", "SELF_ONLY")         # app chưa audit chỉ được SELF_ONLY
META_GRAPH_VERSION = _get("META_GRAPH_VERSION", "v23.0")
FB_PAGE_ID = _get("FB_PAGE_ID")
FB_PAGE_TOKEN = _get("FB_PAGE_TOKEN")
IG_USER_ID = _get("IG_USER_ID")
IG_ACCESS_TOKEN = _get("IG_ACCESS_TOKEN") or FB_PAGE_TOKEN
DEFAULT_PLATFORMS = _list("DEFAULT_PLATFORMS", "youtube,tiktok")

# ================= Chạy song song, lịch tự động =================
MAX_PARALLEL_RENDERS = int(_get("MAX_PARALLEL_RENDERS", "3"))
MAX_CONCURRENT_PROJECTS = int(_get("MAX_CONCURRENT_PROJECTS", "2"))
SCHEDULER_ENABLED = _bool("SCHEDULER_ENABLED", "0")
AUTO_TIMES = _list("AUTO_TIMES", "")               # VD: 08:30,19:45 (giờ máy chủ)
AUTO_DURATION = int(_get("AUTO_DURATION", "30"))
AUTO_PLATFORM_LABEL = _get("AUTO_PLATFORM_LABEL", "TikTok")
AUTO_APPROVE_SCRIPT = _bool("AUTO_APPROVE_SCRIPT", "0")
AUTO_PUBLISH = _bool("AUTO_PUBLISH", "0")
ANALYTICS_TIME = _get("ANALYTICS_TIME", "23:10")
TIMEZONE = _get("TZ", "Asia/Bangkok")

# ================= Chế độ thử =================
# auto = tự dùng dữ liệu giả khi chưa có API key; 1 = luôn giả; 0 = luôn gọi thật
MOCK_CLAUDE = _get("MOCK_CLAUDE", "auto")
MOCK_SEEDANCE = _get("MOCK_SEEDANCE", "auto")
MOCK_MEDIA = _get("MOCK_MEDIA", "auto")     # fal, Pexels, TTS

DATA_ROOT = Path(_get("DATA_ROOT") or (ROOT / "data"))
DATA_DIR = Path(_get("DATA_DIR") or (DATA_ROOT / "projects"))
INSIGHTS_FILE = DATA_ROOT / "insights.md"
for _d in (DATA_DIR, SECRETS_DIR, MUSIC_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def frame_size(resolution: str, ratio: str = "") -> tuple:
    """'720p' + '9:16' -> (720, 1280). Cạnh ngắn = số trước chữ p, làm tròn số chẵn cho FFmpeg."""
    short = int(resolution.lower().rstrip("p"))
    rw, rh = (int(x) for x in (ratio or VIDEO_RATIO).split(":"))
    if rw <= rh:
        w, h = short, short * rh / rw
    else:
        w, h = short * rw / rh, short
    return int(round(w / 2)) * 2, int(round(h / 2)) * 2


def use_mock_claude() -> bool:
    return MOCK_CLAUDE == "1" or (MOCK_CLAUDE == "auto" and not ANTHROPIC_API_KEY)


def use_mock_seedance() -> bool:
    return MOCK_SEEDANCE == "1" or (MOCK_SEEDANCE == "auto" and not ARK_API_KEY)


def mock_media() -> bool:
    return MOCK_MEDIA == "1"


def has_fal() -> bool:
    return bool(FAL_KEY) and not mock_media()


def has_pexels() -> bool:
    return bool(PEXELS_API_KEY) and not mock_media()


def status_summary() -> dict:
    """Hiển thị trên giao diện: module nào đang chạy thật / giả."""
    tts_ok = {"edge": True, "elevenlabs": bool(ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID),
              "fpt": bool(FPT_API_KEY), "none": True}.get(TTS_PROVIDER, False) and not mock_media()
    return {
        "Claude": not use_mock_claude(),
        "Seedance": not use_mock_seedance(),
        "fal.ai": has_fal(),
        "Pexels": has_pexels(),
        f"TTS ({TTS_PROVIDER})": tts_ok,
        "Đăng thật": not PUBLISH_DRY_RUN,
    }
