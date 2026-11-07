"""Đăng TikTok qua Content Posting API (Direct Post).

Cần: app trên developers.tiktok.com có sản phẩm "Content Posting API", scope video.publish,
và access token của tài khoản đăng (lấy qua TikTok Login Kit). App CHƯA qua audit chỉ đăng được
chế độ riêng tư (SELF_ONLY). Đặt TIKTOK_REFRESH_TOKEN + CLIENT_KEY/SECRET để hệ thống tự làm mới token.
"""
import json
import math
import time
from pathlib import Path

import httpx

from .. import config
from ..schemas import Metadata

API = "https://open.tiktokapis.com/v2"
TOKEN_FILE = config.SECRETS_DIR / "tiktok_token.json"


def _token() -> str:
    data = {}
    if TOKEN_FILE.exists():
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    refresh = data.get("refresh_token") or config.TIKTOK_REFRESH_TOKEN
    fresh = data.get("access_token") and data.get("expires_at", 0) > time.time() + 300
    if fresh:
        return data["access_token"]
    if refresh and config.TIKTOK_CLIENT_KEY and config.TIKTOK_CLIENT_SECRET:
        r = httpx.post(f"{API}/oauth/token/", timeout=30, data={
            "client_key": config.TIKTOK_CLIENT_KEY, "client_secret": config.TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token", "refresh_token": refresh})
        j = r.json()
        if "access_token" not in j:
            raise RuntimeError(f"TikTok làm mới token lỗi: {j}")
        j["expires_at"] = time.time() + int(j.get("expires_in", 0))
        TOKEN_FILE.write_text(json.dumps(j), encoding="utf-8")
        return j["access_token"]
    if config.TIKTOK_ACCESS_TOKEN:
        return config.TIKTOK_ACCESS_TOKEN
    raise RuntimeError("Thiếu TIKTOK_ACCESS_TOKEN (hoặc REFRESH_TOKEN + CLIENT_KEY/SECRET)")


def _post(path: str, token: str, body: dict) -> dict:
    r = httpx.post(f"{API}{path}", json=body, timeout=60,
                   headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    j = r.json()
    if (j.get("error") or {}).get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok {path}: {j['error']}")
    return j.get("data", {})


def upload(video: Path, meta: Metadata, log=print) -> dict:
    token = _token()
    info = _post("/post/publish/creator_info/query/", token, {})
    options = info.get("privacy_level_options") or ["SELF_ONLY"]
    privacy = config.TIKTOK_PRIVACY if config.TIKTOK_PRIVACY in options else options[-1]

    size = video.stat().st_size
    chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024
    count = max(1, math.floor(size / chunk))
    data = _post("/post/publish/video/init/", token, {
        "post_info": {"title": meta.tiktok_caption[:2200], "privacy_level": privacy,
                      "disable_comment": False, "disable_duet": False, "disable_stitch": False,
                      "video_cover_timestamp_ms": 1000, "is_aigc": True},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk,
                        "total_chunk_count": count}})
    publish_id, upload_url = data["publish_id"], data["upload_url"]

    with open(video, "rb") as f:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1   # chunk cuối gộp phần dư
            f.seek(start)
            body = f.read(end - start + 1)
            r = httpx.put(upload_url, content=body, timeout=300, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(body)),
                "Content-Range": f"bytes {start}-{end}/{size}"})
            if r.status_code >= 400:
                raise RuntimeError(f"TikTok upload chunk {i} HTTP {r.status_code}: {r.text[:300]}")

    for _ in range(60):                 # chờ TikTok xử lý
        time.sleep(5)
        st = _post("/post/publish/status/fetch/", token, {"publish_id": publish_id})
        status = st.get("status")
        if status == "PUBLISH_COMPLETE":
            ids = st.get("publicaly_available_post_id") or st.get("publicly_available_post_id") or []
            return {"post_id": str(ids[0]) if ids else publish_id, "url": None}
        if status == "FAILED":
            raise RuntimeError(f"TikTok xử lý thất bại: {st.get('fail_reason')}")
    log("TikTok: vẫn đang xử lý, kiểm tra lại trong ứng dụng TikTok.")
    return {"post_id": publish_id, "url": None}
