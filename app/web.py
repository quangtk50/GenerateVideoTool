"""Giao diện web duyệt Cổng 1 và xem demo. Chạy: python run.py"""
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import config, pipeline, storage
from .schemas import STATUS_LABEL, Brief, Scene, Status

app = FastAPI(title="GenerateVideoTool")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
BUSY = {Status.WRITING, Status.DIRECTING, Status.RENDERING, Status.ASSEMBLING}


def _ctx(request: Request, **kw):
    return {"labels": STATUS_LABEL, "busy": BUSY,
            "mock_claude": config.use_mock_claude(), "mock_seedance": config.use_mock_seedance(), **kw}


def _get(pid: str):
    try:
        return storage.load(pid)
    except FileNotFoundError:
        raise HTTPException(404, "Không tìm thấy dự án")


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", _ctx(request, projects=storage.list_all()))


@app.post("/projects")
def create_project(topic: str = Form(...), platform: str = Form("TikTok"), duration: int = Form(30),
                   tone: str = Form("cuốn hút, cảm xúc"), audience: str = Form(""),
                   language: str = Form("Tiếng Việt")):
    p = pipeline.start_project(Brief(topic=topic, platform=platform, duration=duration,
                                     tone=tone, audience=audience, language=language))
    return RedirectResponse(f"/projects/{p.id}", status_code=303)


@app.get("/projects/{pid}")
def view_project(request: Request, pid: str):
    return templates.TemplateResponse(request, "project.html", _ctx(request, p=_get(pid)))


@app.post("/projects/{pid}/script")
async def save_script(request: Request, pid: str):
    """Lưu chỉnh sửa kịch bản; action = save | rewrite | approve."""
    form = await request.form()
    p = _get(pid)
    if p.status != Status.REVIEW_SCRIPT:
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
        pipeline.rewrite_script(pid, form.get("feedback", ""))
        storage.log(pid, f"Yêu cầu viết lại: {form.get('feedback', '')}")
    elif action == "approve":
        storage.log(pid, "Cổng 1: kịch bản được duyệt.")
        pipeline.approve_script(pid)
    else:
        storage.log(pid, "Đã lưu chỉnh sửa kịch bản.")
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.post("/projects/{pid}/shots/{scene_id}/rerender")
def rerender(pid: str, scene_id: int, prompt: str = Form("")):
    p = _get(pid)
    if p.status in BUSY:
        raise HTTPException(400, "Dự án đang chạy, đợi xong rồi thử lại")
    pipeline.rerender_shot(pid, scene_id, prompt)
    storage.log(pid, f"Render lại shot {scene_id}.")
    return RedirectResponse(f"/projects/{pid}", status_code=303)


@app.get("/media/{pid}/{path:path}")
def media(pid: str, path: str):
    base = storage.project_dir(pid).resolve()
    f = (base / path).resolve()
    if base not in f.parents or not f.is_file():
        raise HTTPException(404)
    return FileResponse(f)
