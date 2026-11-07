"""Thumbnail: lấy khung hình đẹp ở cảnh đầu, phủ nền tối dần và chữ lớn."""
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw

from .ffutil import ffmpeg
from .visuals import load_font


def make(source: Path, at: float, text: str, dest: Path, w: int, h: int) -> Path:
    """source: file hình/video gốc của cảnh (chưa có phụ đề)."""
    frame = dest.with_name("thumb_raw.jpg")
    seek = [] if source.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else ["-ss", f"{at:.2f}"]
    ffmpeg([*seek, "-i", str(source), "-frames:v", "1", "-q:v", "2", "-vf",
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", str(frame)])
    img = Image.open(frame).convert("RGB")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(int(h * 0.45), h):            # nền tối dần ở nửa dưới để chữ dễ đọc
        a = int(200 * (y - h * 0.45) / (h * 0.55))
        d.line([(0, y), (w, y)], fill=(0, 0, 0, a))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    size = int(w * 0.11)
    font = load_font(size)
    lines = textwrap.wrap(text.upper(), width=max(8, int(w / (size * 0.62))))[:3]
    y = int(h * 0.78) - len(lines) * int(size * 1.15) // 2
    for line in lines:
        tw = draw.textlength(line, font=font)
        draw.text(((w - tw) / 2, y), line, font=font, fill=(255, 230, 0),
                  stroke_width=max(2, size // 14), stroke_fill=(0, 0, 0))
        y += int(size * 1.15)
    img.convert("RGB").save(dest, quality=92)
    frame.unlink(missing_ok=True)
    return dest
