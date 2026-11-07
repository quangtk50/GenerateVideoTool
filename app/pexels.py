"""Video stock miễn phí từ Pexels (cần ghi nguồn khi có thể; xem điều khoản Pexels)."""
from pathlib import Path

import httpx

from . import config
from .ffutil import download


def find_and_download(query: str, min_seconds: float, dest: Path, target_h: int) -> dict:
    w, h = (int(x) for x in config.VIDEO_RATIO.split(":"))
    orientation = "portrait" if w < h else ("square" if w == h else "landscape")
    r = httpx.get("https://api.pexels.com/videos/search",
                  params={"query": query, "orientation": orientation, "per_page": 15},
                  headers={"Authorization": config.PEXELS_API_KEY}, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Pexels HTTP {r.status_code}: {r.text[:300]}")
    videos = r.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"Pexels không có kết quả cho '{query}'")
    # Ưu tiên video đủ dài, rồi file có chiều cao gần nhất (>=) độ phân giải đích
    long_enough = [v for v in videos if v.get("duration", 0) >= min_seconds]
    video = long_enough[0] if long_enough else max(videos, key=lambda v: v.get("duration", 0))
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("height")]
    if not files:
        raise RuntimeError("Pexels: không có file mp4 phù hợp")
    bigger = sorted([f for f in files if max(f["height"], f["width"]) >= target_h], key=lambda f: f["height"] * f["width"])
    chosen = bigger[0] if bigger else max(files, key=lambda f: f["height"] * f["width"])
    download(chosen["link"], dest)
    return {"pexels_id": video.get("id"), "author": (video.get("user") or {}).get("name"),
            "url": video.get("url"), "duration": video.get("duration")}
