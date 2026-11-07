"""Đăng Facebook Reels (Page) và Instagram Reels qua Meta Graph API (upload resumable).

Cần: Page access token có quyền pages_manage_posts, pages_read_engagement, pages_show_list;
Instagram: tài khoản Business/Creator liên kết Page, quyền instagram_basic, instagram_content_publish.
"""
import time
from pathlib import Path

import httpx

from .. import config
from ..schemas import Metadata


def _g(path: str) -> str:
    return f"https://graph.facebook.com/{config.META_GRAPH_VERSION}/{path.lstrip('/')}"


def _check(r: httpx.Response, step: str) -> dict:
    try:
        j = r.json()
    except ValueError:
        j = {"raw": r.text[:300]}
    if r.status_code >= 400 or "error" in j:
        raise RuntimeError(f"Meta {step}: {j.get('error', j)}")
    return j


def _rupload(url: str, token: str, video: Path) -> None:
    size = video.stat().st_size
    with open(video, "rb") as f:
        r = httpx.post(url, content=f.read(), timeout=600, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)})
    _check(r, "upload")


def facebook_reel(video: Path, meta: Metadata, log=print) -> dict:
    if not (config.FB_PAGE_ID and config.FB_PAGE_TOKEN):
        raise RuntimeError("Thiếu FB_PAGE_ID / FB_PAGE_TOKEN")
    tok = config.FB_PAGE_TOKEN
    start = _check(httpx.post(_g(f"{config.FB_PAGE_ID}/video_reels"), timeout=60,
                              data={"upload_phase": "start", "access_token": tok}), "start")
    vid = start["video_id"]
    _rupload(start.get("upload_url") or
             f"https://rupload.facebook.com/video-upload/{config.META_GRAPH_VERSION}/{vid}", tok, video)
    _check(httpx.post(_g(f"{config.FB_PAGE_ID}/video_reels"), timeout=60, data={
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": meta.facebook_caption, "access_token": tok}), "finish")
    return {"post_id": vid, "url": f"https://www.facebook.com/reel/{vid}"}


def instagram_reel(video: Path, meta: Metadata, log=print) -> dict:
    if not (config.IG_USER_ID and config.IG_ACCESS_TOKEN):
        raise RuntimeError("Thiếu IG_USER_ID / IG_ACCESS_TOKEN")
    tok = config.IG_ACCESS_TOKEN
    c = _check(httpx.post(_g(f"{config.IG_USER_ID}/media"), timeout=60, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": meta.instagram_caption,
        "share_to_feed": "true", "access_token": tok}), "create container")
    cid = c["id"]
    _rupload(c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{config.META_GRAPH_VERSION}/{cid}",
             tok, video)
    for _ in range(60):
        time.sleep(5)
        st = _check(httpx.get(_g(cid), params={"fields": "status_code,status", "access_token": tok},
                              timeout=30), "status")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram xử lý lỗi: {st.get('status')}")
    else:
        raise RuntimeError("Instagram xử lý quá lâu")
    pub = _check(httpx.post(_g(f"{config.IG_USER_ID}/media_publish"), timeout=60,
                            data={"creation_id": cid, "access_token": tok}), "publish")
    return {"post_id": pub["id"], "url": None}
