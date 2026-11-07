"""Bước 11 - Đăng bài. PUBLISH_DRY_RUN=1 (mặc định) chỉ giả lập để thử an toàn."""
from pathlib import Path
from typing import Optional

from .. import config
from ..schemas import Metadata


def publish(platform: str, video: Path, thumb: Optional[Path], meta: Metadata, log=print) -> dict:
    if config.PUBLISH_DRY_RUN:
        log(f"[DRY RUN] Giả lập đăng {platform}: {video.name}")
        return {"post_id": None, "url": None, "dry_run": True}
    if platform == "youtube":
        from . import youtube
        return youtube.upload(video, thumb, meta, log)
    if platform == "tiktok":
        from . import tiktok
        return tiktok.upload(video, meta, log)
    if platform == "facebook":
        from . import meta as m
        return m.facebook_reel(video, meta, log)
    if platform == "instagram":
        from . import meta as m
        return m.instagram_reel(video, meta, log)
    raise ValueError(f"Nền tảng không hỗ trợ: {platform}")
