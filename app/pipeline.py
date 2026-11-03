"""Điều phối các bước. Mỗi thao tác chạy trong thread nền; trạng thái lưu ở project.json."""
import random
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config, storage
from .assembler import assemble_demo
from .director import make_shot_list
from .schemas import Brief, Project, ShotRender, Status
from .script_writer import write_script
from .seedance import render_shot


def _bg(fn, pid: str, *args) -> None:
    def runner():
        try:
            fn(pid, *args)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            storage.log(pid, f"LỖI: {e}")

            def fail(p: Project):
                p.status, p.error = Status.FAILED, str(e)
            storage.update(pid, fail)
    threading.Thread(target=runner, daemon=True).start()


def _cost(pid: str, step: str, info: dict) -> None:
    storage.update(pid, lambda p: p.cost_log.append({"step": step, **info}))


# ---------- Bước 2: viết kịch bản -> Cổng 1 ----------
def start_project(brief: Brief) -> Project:
    p = storage.create(brief)
    _bg(_write, p.id, "")
    return p


def rewrite_script(pid: str, feedback: str) -> None:
    storage.update(pid, lambda p: setattr(p, "status", Status.WRITING))
    _bg(_write, pid, feedback)


def _write(pid: str, feedback: str) -> None:
    p = storage.load(pid)
    storage.log(pid, "Claude bắt đầu viết kịch bản" + (" (theo góp ý)" if feedback else ""))
    script, usage = write_script(p.brief, previous=p.script if feedback else None, feedback=feedback)
    _cost(pid, "script", usage)

    def done(p: Project):
        p.script, p.status, p.error = script, Status.REVIEW_SCRIPT, None
    storage.update(pid, done)
    storage.log(pid, f"Kịch bản xong: {len(script.scenes)} cảnh, {script.total_duration:.0f}s. Chờ duyệt.")


# ---------- Cổng 1 duyệt -> Bước 3, 4, ghép demo ----------
def approve_script(pid: str) -> None:
    storage.update(pid, lambda p: setattr(p, "status", Status.DIRECTING))
    _bg(_direct_and_render, pid)


def _direct_and_render(pid: str) -> None:
    p = storage.load(pid)
    storage.log(pid, "Kịch bản đã duyệt. Claude đang phân cảnh.")
    shot_list, usage = make_shot_list(p.script)
    _cost(pid, "director", usage)
    renders = [ShotRender(scene_id=s.scene_id, seed=random.randint(1, 2**31 - 1)) for s in shot_list.shots]

    def set_shots(p: Project):
        p.shot_list, p.renders, p.status = shot_list, renders, Status.RENDERING
    storage.update(pid, set_shots)
    storage.log(pid, f"Shot list xong ({len(renders)} shot). Bắt đầu render {config.DEMO_RESOLUTION}.")
    _render_all(pid)


def _render_one(pid: str, scene_id: int) -> None:
    p = storage.load(pid)
    shot = next(s for s in p.shot_list.shots if s.scene_id == scene_id)
    scene = next(s for s in p.script.scenes if s.id == scene_id)
    rd = next(r for r in p.renders if r.scene_id == scene_id)
    prompt = shot.prompt
    if p.shot_list.style and p.shot_list.style.lower() not in prompt.lower():
        prompt += f" Style: {p.shot_list.style}."

    def mark(status, **kw):
        def f(p: Project):
            r = next(r for r in p.renders if r.scene_id == scene_id)
            r.status = status
            for k, v in kw.items():
                setattr(r, k, v)
        storage.update(pid, f)

    mark("running", error=None)
    dest = storage.project_dir(pid) / "shots"
    dest.mkdir(exist_ok=True)
    out = dest / f"shot_{scene_id:02d}_{rd.seed}.mp4"
    try:
        info = render_shot(prompt, scene.duration, rd.seed, out)
    except Exception as e:  # noqa: BLE001
        mark("failed", error=str(e))
        storage.log(pid, f"Shot {scene_id} lỗi: {e}")
        raise
    mark("done", task_id=info["task_id"], file=str(out.relative_to(storage.project_dir(pid))))
    _cost(pid, f"seedance_shot_{scene_id}", info)
    storage.log(pid, f"Shot {scene_id} xong.")


def _render_all(pid: str, only=None) -> None:
    p = storage.load(pid)
    ids = [r.scene_id for r in p.renders if (only is None or r.scene_id in only)]
    errors = []
    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_RENDERS) as ex:
        futs = {ex.submit(_render_one, pid, i): i for i in ids}
        for f in as_completed(futs):
            if f.exception():
                errors.append(futs[f])
    if errors:
        raise RuntimeError(f"Các shot lỗi: {sorted(errors)}. Bấm 'Render lại' từng shot để thử lại.")
    _assemble(pid)


def _assemble(pid: str) -> None:
    storage.update(pid, lambda p: setattr(p, "status", Status.ASSEMBLING))
    p = storage.load(pid)
    d = storage.project_dir(pid)
    by_id = {r.scene_id: r for r in p.renders}
    clips = [(s.id, d / by_id[s.id].file) for s in p.script.scenes]
    out = assemble_demo(p.script, clips, d)

    def done(p: Project):
        p.demo_file, p.status, p.error = out.name, Status.DEMO_READY, None
    storage.update(pid, done)
    storage.log(pid, "Demo đã ghép xong.")


def rerender_shot(pid: str, scene_id: int, new_prompt: str = "") -> None:
    """Render lại 1 shot với seed mới (và prompt mới nếu có), rồi ghép lại demo."""
    def prep(p: Project):
        p.status = Status.RENDERING
        r = next(r for r in p.renders if r.scene_id == scene_id)
        r.seed, r.status, r.error = random.randint(1, 2**31 - 1), "pending", None
        if new_prompt.strip():
            next(s for s in p.shot_list.shots if s.scene_id == scene_id).prompt = new_prompt.strip()
    storage.update(pid, prep)
    _bg(_render_all, pid, {scene_id})
