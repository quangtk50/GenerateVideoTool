"""Video/ảnh AI qua fal.ai (một API cho nhiều model: Kling, Wan, Veo, Hailuo, Flux...).

Queue API:
  POST https://queue.fal.run/{model}  -> {request_id, status_url, response_url}
  GET  status_url                     -> {status: IN_QUEUE | IN_PROGRESS | COMPLETED}
  GET  response_url                   -> kết quả (video.url / images[0].url)
Đổi model bằng FAL_VIDEO_MODEL / FAL_IMAGE_MODEL; tham số riêng của model đặt ở FAL_VIDEO_EXTRA (JSON).
"""
import json
import time
from pathlib import Path

import httpx

from . import config
from .ffutil import download


def _headers() -> dict:
    return {"Authorization": f"Key {config.FAL_KEY}", "Content-Type": "application/json"}


def run(model: str, args: dict, timeout: int = 1200) -> dict:
    r = httpx.post(f"https://queue.fal.run/{model}", headers=_headers(), json=args, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"fal.ai HTTP {r.status_code}: {r.text[:400]}")
    job = r.json()
    status_url, response_url = job["status_url"], job["response_url"]
    start = time.time()
    while time.time() - start < timeout:
        s = httpx.get(status_url, headers=_headers(), timeout=60)
        if s.status_code < 400 and s.json().get("status") == "COMPLETED":
            res = httpx.get(response_url, headers=_headers(), timeout=60)
            if res.status_code >= 400:
                raise RuntimeError(f"fal.ai lỗi kết quả HTTP {res.status_code}: {res.text[:400]}")
            return res.json()
        time.sleep(5)
    raise RuntimeError(f"fal.ai quá thời gian chờ {timeout}s ({model})")


def _ratio() -> str:
    return config.VIDEO_RATIO


def render_video(prompt: str, seconds: float, dest: Path) -> dict:
    args = {"prompt": prompt, "aspect_ratio": _ratio(), "duration": "5" if seconds <= 5 else "10"}
    if config.FAL_VIDEO_EXTRA:
        args.update(json.loads(config.FAL_VIDEO_EXTRA))
    res = run(config.FAL_VIDEO_MODEL, args)
    url = (res.get("video") or {}).get("url")
    if not url:
        raise RuntimeError(f"fal.ai không trả video: {str(res)[:300]}")
    download(url, dest)
    return {"model": config.FAL_VIDEO_MODEL, "seconds": args["duration"]}


def render_image(prompt: str, dest: Path) -> dict:
    w, h = (int(x) for x in _ratio().split(":"))
    size = "portrait_16_9" if w < h else ("square_hd" if w == h else "landscape_16_9")
    res = run(config.FAL_IMAGE_MODEL, {"prompt": prompt, "image_size": size, "num_images": 1}, timeout=300)
    imgs = res.get("images") or []
    if not imgs:
        raise RuntimeError(f"fal.ai không trả ảnh: {str(res)[:300]}")
    download(imgs[0]["url"], dest)
    return {"model": config.FAL_IMAGE_MODEL}
