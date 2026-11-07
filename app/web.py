"""Giao diện web: tạo video, duyệt Cổng 1 (kịch bản), Cổng 2 (video + metadata), đăng bài, thống kê.
Chạy: python run.py  ->  http://127.0.0.1:8000"""
import base64
import secrets
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import analytics, config, pipeline, scheduler, storage
from .schemas import BUSY, PLATFORMS, STATUS_LABEL, Brief, Scene, Status


@asynccontextmanager
async def lifespan(_app):
    pipeline.recover_interrupted()
    scheduler.start()
    yield

app = FastAPI(title="GenerateVideoTool", lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    """Bật khi đặt WEB_USER + WEB_PASSWORD (bắt buộc nên bật khi đưa lên VPS)."""
    if config.WEB_USER and config.WEB_PASSWORD and request.url.path != "/healthz":
        ok = False
        h = request.headers.get("authorization", "")
        if h.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(h[6:]).decode().partition(":")
                ok = secrets.compare_digest(user, config.WEB_USER) and secrets.compare_digest(pw, config.WEB_PASSWORD)
            except Exception:  # noqa: BLE001
                ok = False
        if not ok:
            return Response("Cần đăng nhập", status_code=401, headers={"WWW-Authenticate": 'Basic realm="GVT"'})
    return await call_next(request)


def _ctx(**kw):
    return {"labels": STATUS_LABEL, "busy": BUSY, "resolutions": config.RESOLUTION_OPTIONS,
            "default_resolution": config.DEFAULT_RESOLUTION, "frame_size": config.frame_size,
            "modules": config.status_summary(), "platforms": PLATFORMS,
            "default_platforms": config.DEFAULT_PLATFORMS, "dry_run": config.PUBLISH_DRY_RUN, **kw}


def _get(pid: str):
    try:
        return storage.load(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Không tìm thấy dự án")


def _back(pid: str):
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", _ctx(projects=storage.list_all()))


def _brief(topic, platform, duration, tone, audience, language, resolution, visual_mode, with_music,
           platforms, auto_approve_script, auto_publish) -> Brief:
    return Brief(topic=topic, platform=platform, duration=duration, tone=tone, audience=audience,
                 language=language, resolution=resolution, visual_mode=visual_mode,
                 with_music=bool(with_music), platforms=[x for x in platforms if x in PLATFORMS],
                 auto_approve_script=bool(auto_approve_script), auto_publish=bool(auto_publish))


@app.post("/projects")
def create_project(topic: str = Form(""), platform: str = Form("TikTok"), duration: int = Form(30),
                   tone: str = Form("cuốn hút, cảm xúc"), audience: str = Form(""),
                   language: str = Form("Tiếng Việt"), resolution: str = Form(""),
                   visual_mode: str = Form("auto"), with_music: str = Form(""),
                   platforms: List[str] = Form([]), auto_approve_script: str = Form(""),
                   auto_publish: str = Form(""), mode: str = Form("manual")):
    b = _brief(topic, platform, duration, tone, audience, language, resolution, visual_mode, with_music,
               platforms, auto_approve_script, auto_publish)
    if mode == "auto" or not topic.strip():
        p = pipeline.start_auto_project(b)
    else:
        p = pipeline.start_project(b)
    return _back(p.id)


@app.get("/projects/{pid}")
def view_project(request: Request, pid: str):
    p = _get(pid)
    cl = p.cost_log
    cost = {"tin": sum(c.get("input_tokens", 0) for c in cl), "tout": sum(c.get("output_tokens", 0) for c in cl),
            "visuals": sum(1 for c in cl if str(c.get("step", "")).startswith(("visual_", "seedance_"))),
            "tts_chars": sum(c.get("chars", 0) for c in cl)}
    return templates.TemplateResponse(request, "project.html",
                                      _ctx(p=p, cost=cost, durations=p.scene_durations() if p.script else {}))


@app.get("/api/projects/{pid}")
def api_project(pid: str):
    return _get(pid).model_dump()


@app.post("/projects/{pid}/script")
async def save_script(request: Request, pid: str):
    """Cổng 1: lưu chỉnh sửa kịch bản; action = save | rewrite | approve."""
    form = await request.form()
    p = _get(pid)
    if p.status not in (Status.REVIEW_SCRIPT, Status.FAILED) or not p.script:
        raise HTTPException(400, "Kịch bản không ở trạng thái chờ duyệt")
    s = p.script
    s.title = form.get("title", s.title)
    s.hook = form.get("hook", s.hook)
    s.cta = form.get("cta", s.cta)
    scenes = []
    for sc in s.scenes:
        if form.get(f"scene_{sc.id}_delete"):
            continue
        scenes.append(Scene(id=sc.id,
                            duration=float(form.get(f"scene_{sc.id}_duration", sc.duration)),
                            visual=form.get(f"scene_{sc.id}_visual", sc.visual),
                            voiceover=form.get(f"scene_{sc.id}_voiceover", sc.voiceover)))
    for i, sc in enumerate(scenes, start=1):   # đánh số lại sau khi xoá cảnh
        sc.id = i
    s.scenes = scenes
    storage.update(pid, lambda x: setattr(x, "script", s))

    action = form.get("action", "save")
    if action == "rewrite":
        storage.log(pid, f"Yêu cầu viết lại: {form.get('feedback', '')}")
        pipeline.rewrite_script(pid, form.get("feedback", ""))
    elif action == "approve":
        storage.log(pid, "Cổng 1: kịch bản được duyệt.")
        pipeline.approve_script(pid)
    else:
        storage.log(pid, "Đã lưu chỉnh sửa kịch bản.")
    return _back(pid)


@app.post("/projects/{pid}/shots/{scene_id}/rerender")
def rerender(pid: str, scene_id: int, prompt: str = Form(""), source: str = Form("")):
    p = _get(pid)
    if p.status in BUSY:
        raise HTTPException(400, "Dự án đang chạy, đợi xong rồi thử lại")
    storage.log(pid, f"Render lại shot {scene_id}.")
    pipeline.rerender_shot(pid, scene_id, prompt, source or None)
    return _back(pid)


@app.post("/projects/{pid}/final")
async def final_review(request: Request, pid: str):
    """Cổng 2: lưu metadata; action = save | publish."""
    form = await request.form()
    p = _get(pid)
    if not p.metadata:
        raise HTTPException(400, "Chưa có metadata")
    m = p.metadata
    for f in ("youtube_title", "youtube_description", "tiktok_caption", "facebook_caption",
              "instagram_caption", "thumbnail_text"):
        if f in form:
            setattr(m, f, str(form[f]))
    if "tags" in form:
        m.tags = [t.strip() for t in str(form["tags"]).split(",") if t.strip()]
    storage.update(pid, lambda x: setattr(x, "metadata", m))
    if form.get("action") == "publish":
        plats = [x for x in form.getlist("platforms") if x in PLATFORMS]
        if not plats:
            raise HTTPException(400, "Chọn ít nhất 1 nền tảng")
        storage.log(pid, f"Cổng 2: duyệt đăng {', '.join(plats)}.")
        pipeline.approve_publish(pid, plats)
    else:
        storage.log(pid, "Đã lưu metadata.")
    return _back(pid)


@app.post("/projects/{pid}/resume")
def resume(pid: str):
    p = _get(pid)
    if p.status in BUSY:
        raise HTTPException(400, "Dự án đang chạy")
    storage.log(pid, "Tiếp tục chạy.")
    pipeline.resume(pid)
    return _back(pid)


@app.get("/insights")
def insights(request: Request):
    text = config.INSIGHTS_FILE.read_text(encoding="utf-8") if config.INSIGHTS_FILE.exists() else ""
    rows = [p for p in storage.list_all() if p.stats]
    return templates.TemplateResponse(request, "insights.html", _ctx(text=text, rows=rows))


@app.post("/insights/run")
def run_insights():
    threading.Thread(target=analytics.run, daemon=True).start()
    return RedirectResponse("/insights", status_code=303)


@app.get("/media/{pid}/{path:path}")
def media(pid: str, path: str):
    base = storage.project_dir(pid).resolve()
    f = (base / path).resolve()
    if base not in f.parents or not f.is_file():
        raise HTTPException(404)
    return FileResponse(f)
