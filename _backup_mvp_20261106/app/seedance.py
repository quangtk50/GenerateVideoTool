"""Bước 4 - Gọi Seedance (BytePlus ModelArk) để render từng shot.

REST:
  POST {ARK_BASE_URL}/contents/generations/tasks      -> {"id": "..."}
  GET  {ARK_BASE_URL}/contents/generations/tasks/{id} -> {"status": ..., "content": {"video_url": ...}}
"""
import math
import subprocess
import time
from pathlib import Path
from typing import Optional

import httpx

from . import config


class SeedanceError(RuntimeError):
    pass


def api_duration(seconds: float) -> int:
    """Làm tròn lên và kẹp trong giới hạn của model; phần thừa sẽ được cắt khi ghép."""
    return max(config.SEEDANCE_MIN_DURATION, min(config.SEEDANCE_MAX_DURATION, math.ceil(seconds)))


class SeedanceClient:
    def __init__(self) -> None:
        self.http = httpx.Client(
            base_url=config.ARK_BASE_URL,
            headers={"Authorization": f"Bearer {config.ARK_API_KEY}",
                     "Content-Type": "application/json"},
            timeout=60,
        )

    def create(self, prompt: str, duration: int, resolution: str, ratio: str,
               seed: Optional[int] = None, first_frame_url: Optional[str] = None) -> str:
        content = [{"type": "text", "text": prompt}]
        if first_frame_url:
            content.append({"type": "image_url", "image_url": {"url": first_frame_url}, "role": "first_frame"})
        body = {
            "model": config.SEEDANCE_MODEL,
            "content": content,
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
            "generate_audio": False,   # nhạc ghép riêng ở bước sau
            "watermark": False,
        }
        if seed is not None and config.SEEDANCE_SEND_SEED:
            body["seed"] = seed
        r = self._request("POST", "/contents/generations/tasks", json=body)
        task_id = r.get("id")
        if not task_id:
            raise SeedanceError(f"Không nhận được task id: {r}")
        return task_id

    def get(self, task_id: str) -> dict:
        return self._request("GET", f"/contents/generations/tasks/{task_id}")

    def wait(self, task_id: str, timeout: int = 1200, interval: int = 8) -> dict:
        start = time.time()
        while time.time() - start < timeout:
            r = self.get(task_id)
            status = r.get("status")
            if status == "succeeded":
                return r
            if status in ("failed", "cancelled", "expired"):
                raise SeedanceError(f"Task {task_id} {status}: {r.get('error')}")
            time.sleep(interval)
        raise SeedanceError(f"Task {task_id} quá thời gian chờ {timeout}s")

    def download(self, url: str, dest: Path) -> None:
        with httpx.stream("GET", url, timeout=300, follow_redirects=True) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)

    def _request(self, method: str, path: str, **kw) -> dict:
        for attempt in range(4):
            try:
                r = self.http.request(method, path, **kw)
            except httpx.TransportError as e:
                err = str(e)
            else:
                if r.status_code == 429 or r.status_code >= 500:
                    err = f"HTTP {r.status_code}: {r.text[:300]}"
                elif r.status_code >= 400:
                    raise SeedanceError(f"HTTP {r.status_code}: {r.text[:500]}")
                else:
                    return r.json()
            time.sleep(2 ** attempt * 3)  # backoff: 3s, 6s, 12s, 24s
        raise SeedanceError(f"Gọi API thất bại sau nhiều lần thử: {err}")


def render_shot(prompt: str, seconds: float, seed: int, dest: Path,
                resolution: Optional[str] = None) -> dict:
    """Render 1 shot ra file mp4. Trả về thông tin để ghi log (task_id, usage)."""
    duration = api_duration(seconds)
    resolution = resolution or config.DEMO_RESOLUTION
    if config.use_mock_seedance():
        _mock_render(duration, seed, dest, resolution)
        return {"task_id": f"mock-{seed}", "usage": {"mock": True, "seconds": duration}}

    client = SeedanceClient()
    task_id = client.create(prompt, duration, resolution, config.VIDEO_RATIO, seed=seed)
    result = client.wait(task_id)
    url = (result.get("content") or {}).get("video_url")
    if not url:
        raise SeedanceError(f"Task {task_id} không có video_url: {result}")
    client.download(url, dest)
    return {"task_id": task_id, "usage": result.get("usage", {})}


def _mock_render(duration: int, seed: int, dest: Path, resolution: str = "480p") -> None:
    """Video giả (màn hình test) để chạy thử pipeline không tốn tiền."""
    hue = seed % 360
    w, h = config.frame_size(resolution)
    cmd = [config.FFMPEG_BIN, "-y", "-loglevel", "error",
           "-f", "lavfi", "-i", f"testsrc2=s={w}x{h}:r=24:d={duration}",
           "-vf", f"hue=h={hue}", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)]
    subprocess.run(cmd, check=True)
    time.sleep(1)
