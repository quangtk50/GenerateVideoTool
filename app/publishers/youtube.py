"""Đăng YouTube (Shorts) qua YouTube Data API v3.

Lần đầu: tải OAuth client (loại Desktop app) từ Google Cloud về data/secrets/youtube_client_secret.json
rồi chạy:  python -m app.cli youtube-auth   -> mở trình duyệt đăng nhập -> lưu data/secrets/youtube_token.json
"""
from pathlib import Path
from typing import Dict, List

from .. import config
from ..schemas import Metadata

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]


def get_credentials(interactive: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = None
    if config.YOUTUBE_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(config.YOUTUBE_TOKEN), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        config.YOUTUBE_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    if creds and creds.valid:
        return creds
    if not interactive:
        raise RuntimeError("Chưa đăng nhập YouTube. Chạy: python -m app.cli youtube-auth")
    if not config.YOUTUBE_CLIENT_SECRET.exists():
        raise RuntimeError(f"Thiếu file OAuth client: {config.YOUTUBE_CLIENT_SECRET}")
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(str(config.YOUTUBE_CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=8765, open_browser=True, prompt="consent")
    config.YOUTUBE_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _client():
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=get_credentials(), cache_discovery=False)


def upload(video: Path, thumb: Path, meta: Metadata, log=print) -> dict:
    from googleapiclient.http import MediaFileUpload

    yt = _client()
    title = meta.youtube_title[:100]
    body = {
        "snippet": {"title": title, "description": meta.youtube_description[:4900],
                    "tags": meta.tags[:30], "categoryId": config.YOUTUBE_CATEGORY_ID},
        "status": {"privacyStatus": config.YOUTUBE_PRIVACY, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},   # nhãn "nội dung do AI tạo/chỉnh sửa"
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), mimetype="video/mp4",
                                                        chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    if thumb and thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        except Exception as e:  # noqa: BLE001 - kênh chưa xác minh không đặt được thumbnail
            log(f"YouTube: không đặt được thumbnail ({str(e)[:150]})")
    return {"post_id": vid, "url": f"https://youtube.com/shorts/{vid}"}


def stats(video_ids: List[str]) -> Dict[str, dict]:
    if not video_ids:
        return {}
    yt = _client()
    out = {}
    for i in range(0, len(video_ids), 50):
        resp = yt.videos().list(part="statistics", id=",".join(video_ids[i:i + 50])).execute()
        for item in resp.get("items", []):
            s = item.get("statistics", {})
            out[item["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                               "comments": int(s.get("commentCount", 0))}
    return out
