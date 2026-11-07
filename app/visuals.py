"""Bước 6 - Định tuyến nguồn hình cho từng cảnh: AI video / AI ảnh / video stock.

Mỗi shot có source do đạo diễn chọn. Nếu nhà cung cấp chưa cấu hình hoặc lỗi,
hệ thống tự chuyển sang nguồn kế tiếp; không có nguồn nào thì dùng hình giả (chế độ thử).
"""
import random
from pathlib import Path
from typing import Callable, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from . import config, fal_ai, pexels, seedance
from .ffutil import ffmpeg
from .schemas import Shot

FALLBACK = {
    "ai_video": ["ai_video", "ai_image", "stock"],
    "ai_image": ["ai_image", "stock", "ai_video"],
    "stock": ["stock", "ai_image", "ai_video"],
}


def _video_providers() -> List[str]:
    avail = []
    if not config.use_mock_seedance() and not config.mock_media():
        avail.append("seedance")
    if config.has_fal():
        avail.append("fal")
    avail.sort(key=lambda p: p != config.VIDEO_PROVIDER)   # nhà cung cấp chính lên đầu
    return avail


def available(source: str) -> List[str]:
    if source == "ai_video":
        return _video_providers()
    if source == "ai_image":
        return ["fal"] if config.has_fal() else []
    if source == "stock":
        return ["pexels"] if config.has_pexels() else []
    return []


def render(shot: Shot, style: str, seconds: float, seed: int, out_dir: Path,
           resolution: str, log: Callable[[str], None] = print) -> Tuple[Path, str, str, dict]:
    """Trả về (file, nguồn đã dùng, nhà cung cấp, thông tin chi phí)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = shot.prompt
    if style and style.lower() not in prompt.lower():
        prompt += f" Style: {style}."
    base = out_dir / f"shot_{shot.scene_id:02d}_{seed}"
    errors = []
    for source in FALLBACK.get(shot.source, FALLBACK["ai_video"]):
        for provider in available(source):
            try:
                if source == "ai_video" and provider == "seedance":
                    dest = base.with_suffix(".mp4")
                    info = seedance.render_shot(prompt, seconds, seed, dest, resolution)
                elif source == "ai_video" and provider == "fal":
                    dest = base.with_suffix(".mp4")
                    info = fal_ai.render_video(prompt, seconds, dest)
                elif source == "ai_image":
                    dest = base.with_suffix(".jpg")
                    info = fal_ai.render_image(prompt, dest)
                else:
                    dest = base.with_suffix(".mp4")
                    _, h = config.frame_size(resolution)
                    info = pexels.find_and_download(shot.stock_query or shot.action, seconds, dest, h)
                if source != shot.source:
                    log(f"Shot {shot.scene_id}: chuyển {shot.source} → {source} ({provider})")
                return dest, source, provider, info
            except Exception as e:  # noqa: BLE001
                errors.append(f"{source}/{provider}: {e}")
                log(f"Shot {shot.scene_id}: {source}/{provider} lỗi, thử nguồn khác. {str(e)[:200]}")
    if errors:
        raise RuntimeError("Mọi nguồn hình đều lỗi: " + " | ".join(errors)[:800])
    # Chưa cấu hình nguồn nào -> hình giả để chạy thử trọn luồng
    return _mock(shot, seconds, seed, base, resolution)


def _mock(shot: Shot, seconds: float, seed: int, base: Path, resolution: str):
    w, h = config.frame_size(resolution)
    if shot.source == "ai_image":
        dest = base.with_suffix(".jpg")
        mock_image(f"Cảnh {shot.scene_id}\n{shot.action[:80]}", dest, w, h, seed)
        return dest, "ai_image", "mock", {"mock": True}
    dest = base.with_suffix(".mp4")
    dur = max(config.SEEDANCE_MIN_DURATION, int(seconds) + 1)
    ffmpeg(["-f", "lavfi", "-i", f"testsrc2=s={w}x{h}:r={config.FPS}:d={dur}",
            "-vf", f"hue=h={seed % 360}", "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", str(dest)])
    return dest, shot.source, "mock", {"mock": True, "seconds": dur}


def find_font(bold: bool = True) -> str:
    """Tìm font TTF hỗ trợ tiếng Việt trên Windows / Linux / macOS."""
    if config.THUMB_FONT and Path(config.THUMB_FONT).exists():
        return config.THUMB_FONT
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return ""


def load_font(size: int, bold: bool = True):
    f = find_font(bold)
    return ImageFont.truetype(f, size) if f else ImageFont.load_default()


def mock_image(text: str, dest: Path, w: int, h: int, seed: int) -> None:
    rnd = random.Random(seed)
    c1 = tuple(rnd.randint(30, 200) for _ in range(3))
    c2 = tuple(rnd.randint(30, 200) for _ in range(3))
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    font = load_font(max(18, w // 18))
    draw.multiline_text((w // 12, h // 3), text, font=font, fill=(255, 255, 255), spacing=8)
    img.save(dest, quality=90)
