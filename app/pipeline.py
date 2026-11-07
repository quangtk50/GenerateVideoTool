"""Bộ điều phối (Orchestrator): chạy các bước theo thứ tự, lưu trạng thái sau mỗi bước.

Mỗi bước đều "idempotent": chạy lại sẽ bỏ qua phần đã xong (shot đã render, lời thoại đã tạo...),
nên khi lỗi giữa chừng hoặc khởi động lại máy chỉ cần bấm "Tiếp tục".

Luồng:  ý tưởng → kịch bản → phản biện (vòng lặp) → Cổng 1 → đạo diễn → lời thoại → hình/video
        → nhạc → dựng → QA → SEO + thumbnail → Cổng 2 → đăng bài → (thống kê, chạy theo lịch)
"""
import random
import shutil
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional

from . import config, music, publishers, storage, thumbnail, tts, visuals
from .assembler import assemble
from .critic import critique, feedback_text
from .director import make_shot_list
from .idea_generator import generate_idea
from .qa import check as qa_check
from .schemas import BUSY, Brief, Project, PublishResult, SceneAudio, ShotRender, Status
from .script_writer import write_script
from .seo import make_metadata

AUTO_PLACEHOLDER = "(AI đang tự nghĩ ý tưởng…)"
_production_slots = threading.BoundedSemaphore(config.MAX_CONCURRENT_PROJECTS)


# ---------------- tiện ích ----------------
def _bg(fn, pid: str, *args) -> None:
    """Chạy 1 bước trong thread nền; lỗi -> trạng thái FAILED kèm thông báo."""
    def runner():
        try:
            fn(pid, *args)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            fail(pid, e)
    threading.Thread(target=runner, daemon=True).start()


def fail(pid: str, e: Exception) -> None:
    storage.log(pid, f"LỖI: {e}")

    def f(p: Project):
        p.status, p.error = Status.FAILED, str(e)[:2000]
    storage.update(pid, f)


def _cost(pid: str, step: str, info: dict) -> None:
    storage.update(pid, lambda p: p.cost_log.append({"step": step, **(info or {})}))


def _logger(pid: str):
    return lambda msg: storage.log(pid, msg)


# ---------------- Tạo dự án ----------------
def _defaults(brief: Brief) -> Brief:
    if not brief.platforms:
        brief.platforms = list(config.DEFAULT_PLATFORMS)
    if brief.resolution not in config.RESOLUTION_OPTIONS:
        brief.resolution = config.DEFAULT_RESOLUTION
    return brief


def start_project(brief: Brief, background: bool = True) -> Project:
    p = storage.create(_defaults(brief), Status.WRITING)
    if background:
        _bg(write_flow, p.id, "")
    return p


def start_auto_project(brief: Brief, background: bool = True) -> Project:
    """Không cần nhập chủ đề: Claude tự nghĩ ý tưởng rồi viết kịch bản luôn."""
    brief.topic = AUTO_PLACEHOLDER
    p = storage.create(_defaults(brief), Status.IDEATING)
    if background:
        _bg(auto_flow, p.id)
    return p


def auto_flow(pid: str) -> None:
    p = storage.load(pid)
    storage.log(pid, "Claude đang tự nghĩ ý tưởng")
    recent = [x.brief.topic for x in storage.list_all()[:30]
              if x.id != pid and x.brief.topic != AUTO_PLACEHOLDER]
    idea, usage = generate_idea(p.brief, recent)
    _cost(pid, "idea", usage)

    def apply(p: Project):
        p.brief.topic, p.brief.audience, p.brief.tone = idea.topic, idea.audience, idea.tone
    storage.update(pid, apply)
    storage.log(pid, f"Ý tưởng: {idea.topic} — {idea.reason}")
    write_flow(pid, "")


# ---------------- Bước 2: kịch bản + phản biện -> Cổng 1 ----------------
def write_flow(pid: str, feedback: str) -> None:
    storage.set_status(pid, Status.WRITING)
    p = storage.load(pid)
    storage.log(pid, "Claude bắt đầu viết kịch bản" + (" (theo góp ý)" if feedback else ""))
    script, usage = write_script(p.brief, previous=p.script if feedback else None, feedback=feedback)
    _cost(pid, "script", usage)
    storage.update(pid, lambda x: setattr(x, "script", script))

    if config.CRITIC_ENABLED:
        for rnd in range(1, config.CRITIC_MAX_ROUNDS + 1):
            storage.set_status(pid, Status.CRITIQUING)
            c, usage = critique(p.brief, script)
            _cost(pid, f"critic_{rnd}", usage)
            storage.update(pid, lambda x: x.critiques.append(c))
            storage.log(pid, f"Phản biện vòng {rnd}: {c.score}/10 (hook {c.hook_score}/10)")
            if c.score >= config.CRITIC_MIN_SCORE or rnd == config.CRITIC_MAX_ROUNDS:
                break
            storage.set_status(pid, Status.WRITING)
            storage.log(pid, "Điểm chưa đạt, biên kịch viết lại theo góp ý của agent phản biện")
            script, usage = write_script(p.brief, previous=script, feedback=feedback_text(c))
            _cost(pid, f"script_rewrite_{rnd}", usage)
            storage.update(pid, lambda x: setattr(x, "script", script))

    storage.set_status(pid, Status.REVIEW_SCRIPT)
    storage.log(pid, f"Kịch bản xong: {len(script.scenes)} cảnh, {script.total_duration:.0f}s. Chờ duyệt.")
    if storage.load(pid).brief.auto_approve_script:
        storage.log(pid, "Tự động duyệt kịch bản (auto_approve_script).")
        approve_script(pid, background=False)


def rewrite_script(pid: str, feedback: str) -> None:
    storage.set_status(pid, Status.WRITING)
    _bg(write_flow, pid, feedback)


# ---------------- Cổng 1 duyệt -> sản xuất ----------------
def approve_script(pid: str, background: bool = True) -> None:
    def f(p: Project):
        p.script_approved, p.status = True, Status.DIRECTING
    storage.update(pid, f)
    if background:
        _bg(produce, pid)
    else:
        produce(pid)


def produce(pid: str) -> None:
    storage.log(pid, "Chờ lượt sản xuất…")
    with _production_slots:
        _direct(pid)
        _voice(pid)
        _render_all(pid)
        _assemble(pid)
        _qa(pid)
        _package(pid)
    p = storage.load(pid)
    if p.brief.auto_publish and p.brief.platforms:
        if p.qa and not p.qa.passed:
            storage.set_status(pid, Status.REVIEW_FINAL)
            storage.log(pid, "QA phát hiện lỗi nghiêm trọng → KHÔNG tự đăng, chờ duyệt tay (Cổng 2).")
            return
        publish_flow(pid)
    else:
        storage.set_status(pid, Status.REVIEW_FINAL)
        storage.log(pid, "Video hoàn chỉnh. Chờ duyệt để đăng (Cổng 2).")


def _direct(pid: str) -> None:
    p = storage.load(pid)
    if p.shot_list:
        return
    storage.set_status(pid, Status.DIRECTING)
    storage.log(pid, "Claude đang phân cảnh, chọn góc máy và nguồn hình.")
    mode = p.brief.visual_mode if p.brief.visual_mode != "auto" else config.VISUAL_MODE
    shot_list, usage = make_shot_list(p.script, mode)
    _cost(pid, "director", usage)
    srcs = ", ".join(f"{s.scene_id}:{s.source}" for s in shot_list.shots)
    storage.update(pid, lambda x: setattr(x, "shot_list", shot_list))
    storage.log(pid, f"Shot list xong ({len(shot_list.shots)} shot) — nguồn: {srcs}")


def _voice(pid: str) -> None:
    storage.set_status(pid, Status.VOICING)
    p = storage.load(pid)
    vdir = storage.project_dir(pid) / "voice"
    vdir.mkdir(exist_ok=True)
    old = {v.scene_id: v for v in p.voices}
    voices: List[SceneAudio] = []
    made = 0
    for sc in p.script.scenes:
        text = sc.voiceover.strip()
        v = old.get(sc.id)
        if v and v.text == text and (not v.file or (vdir / v.file).exists()):
            voices.append(v)
            continue
        if text:
            v = tts.synthesize(text, vdir / f"scene_{sc.id:02d}", p.brief.voice)
            made += 1
            _cost(pid, f"tts_{sc.id}", {"provider": v.provider, "chars": len(text)})
        else:
            v = SceneAudio(scene_id=sc.id, text="")
        v.scene_id = sc.id
        voices.append(v)
    storage.update(pid, lambda x: setattr(x, "voices", voices))
    if made:
        total = sum(v.duration for v in voices)
        storage.log(pid, f"Lời thoại xong: {made} đoạn, tổng {total:.1f}s ({config.TTS_PROVIDER}).")


def _render_one(pid: str, scene_id: int) -> None:
    p = storage.load(pid)
    shot = next(s for s in p.shot_list.shots if s.scene_id == scene_id)
    rd = next(r for r in p.renders if r.scene_id == scene_id)
    seconds = p.scene_durations()[scene_id]

    def mark(**kw):
        def f(p: Project):
            r = next(r for r in p.renders if r.scene_id == scene_id)
            for k, v in kw.items():
                setattr(r, k, v)
        storage.update(pid, f)

    mark(status="running", error=None)
    d = storage.project_dir(pid)
    try:
        out, source, provider, info = visuals.render(shot, p.shot_list.style, seconds, rd.seed, d / "shots",
                                                     p.brief.resolution, log=_logger(pid))
    except Exception as e:  # noqa: BLE001
        mark(status="failed", error=str(e)[:500])
        storage.log(pid, f"Shot {scene_id} lỗi: {e}")
        raise
    mark(status="done", file=out.relative_to(d).as_posix(), source=source, provider=provider,
         task_id=str(info.get("task_id", "")) or None)
    _cost(pid, f"visual_{scene_id}", {"source": source, "provider": provider, **info})
    storage.log(pid, f"Shot {scene_id} xong ({source}/{provider}).")


def _render_all(pid: str) -> None:
    storage.set_status(pid, Status.RENDERING)

    def sync(p: Project):     # đảm bảo mỗi shot có 1 bản ghi render
        for r in p.renders:   # dự án cũ tạo trên Windows lưu "shots\\x.mp4"
            if r.file:
                r.file = r.file.replace("\\", "/")
        have = {r.scene_id for r in p.renders}
        for s in p.shot_list.shots:
            if s.scene_id not in have:
                p.renders.append(ShotRender(scene_id=s.scene_id, seed=random.randint(1, 2**31 - 1)))
        p.renders.sort(key=lambda r: r.scene_id)
    p = storage.update(pid, sync)
    d = storage.project_dir(pid)
    todo = [r.scene_id for r in p.renders
            if r.status != "done" or not r.file or not (d / r.file).exists()]
    if not todo:
        return
    storage.log(pid, f"Tạo hình cho {len(todo)} shot ({p.brief.resolution}).")
    errors = []
    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_RENDERS) as ex:
        futs = {ex.submit(_render_one, pid, i): i for i in todo}
        for f in as_completed(futs):
            if f.exception():
                errors.append(futs[f])
    if errors:
        raise RuntimeError(f"Các shot lỗi: {sorted(errors)}. Sửa prompt/nguồn rồi bấm 'Render lại' hoặc 'Tiếp tục'.")


def _assemble(pid: str) -> None:
    storage.set_status(pid, Status.ASSEMBLING)
    p = storage.load(pid)
    d = storage.project_dir(pid)
    mfile = None
    if p.brief.with_music:
        if p.music_file and (config.MUSIC_DIR / p.music_file).exists():
            mfile = config.MUSIC_DIR / p.music_file
        else:
            mfile = music.pick(p.script.music_brief, seed=hash(pid) & 0xFFFF)
            if mfile:
                rel = mfile.relative_to(config.MUSIC_DIR).as_posix()
                storage.update(pid, lambda x: setattr(x, "music_file", rel))
            else:
                storage.log(pid, "Chưa có nhạc trong assets/music → video không có nhạc nền.")
    storage.log(pid, "FFmpeg đang dựng video: ghép cảnh, lời thoại, phụ đề, nhạc, chuẩn hoá âm lượng.")
    out = assemble(p, d, mfile, log=_logger(pid))
    storage.update(pid, lambda x: setattr(x, "final_file", out.name))
    storage.log(pid, f"Dựng xong: {out.name} ({sum(p.scene_durations().values()):.1f}s).")


def _qa(pid: str) -> None:
    storage.set_status(pid, Status.QA)
    p = storage.load(pid)
    d = storage.project_dir(pid)
    report, usage = qa_check(p, d / p.final_file, d)
    _cost(pid, "qa", usage)
    storage.update(pid, lambda x: setattr(x, "qa", report))
    high = [i for i in report.issues if i.severity == "high"]
    storage.log(pid, f"QA: {'ĐẠT' if report.passed else 'CÓ LỖI'} — {len(report.issues)} ghi chú, {len(high)} lỗi nặng.")


def _package(pid: str) -> None:
    storage.set_status(pid, Status.PACKAGING)
    p = storage.load(pid)
    d = storage.project_dir(pid)
    if not p.metadata:
        meta, usage = make_metadata(p.brief, p.script)
        _cost(pid, "seo", usage)
        storage.update(pid, lambda x: setattr(x, "metadata", meta))
        p = storage.load(pid)
    first = p.script.scenes[0].id
    at = min(p.scene_durations()[first] / 2, 2.0)
    src = d / next(r.file for r in p.renders if r.scene_id == first)
    w, h = config.frame_size(p.brief.resolution)
    thumbnail.make(src, at, p.metadata.thumbnail_text, d / "thumbnail.jpg", w, h)
    storage.update(pid, lambda x: setattr(x, "thumbnail_file", "thumbnail.jpg"))
    shutil.rmtree(d / "tmp", ignore_errors=True)
    storage.log(pid, "Đã tạo tiêu đề, mô tả, hashtag và thumbnail.")


# ---------------- Cổng 2 -> đăng bài ----------------
def approve_publish(pid: str, platforms: List[str], background: bool = True) -> None:
    def f(p: Project):
        p.brief.platforms = platforms
        p.status = Status.PUBLISHING
    storage.update(pid, f)
    if background:
        _bg(publish_flow, pid)
    else:
        publish_flow(pid)


def publish_flow(pid: str) -> None:
    storage.set_status(pid, Status.PUBLISHING)
    p = storage.load(pid)
    d = storage.project_dir(pid)
    video = d / p.final_file
    thumb = d / p.thumbnail_file if p.thumbnail_file else None
    ok = 0
    for platform in p.brief.platforms:
        prev = next((r for r in p.publish if r.platform == platform), None)
        if prev and prev.status == "done":
            ok += 1
            continue
        storage.log(pid, f"Đang đăng {platform}…")
        res = PublishResult(platform=platform, status="running")
        try:
            out = publishers.publish(platform, video, thumb, p.metadata, log=_logger(pid))
            res.status = "dry_run" if out.get("dry_run") else "done"
            res.post_id, res.url = out.get("post_id"), out.get("url")
            ok += 1
            storage.log(pid, f"Đăng {platform}: {res.status} {res.url or res.post_id or ''}")
        except Exception as e:  # noqa: BLE001 - lỗi 1 nền tảng không chặn nền tảng khác
            res.status, res.error = "failed", str(e)[:800]
            storage.log(pid, f"Đăng {platform} lỗi: {e}")
        res.at = datetime.now().isoformat(timespec="seconds")

        def save(p: Project, res=res):
            p.publish = [r for r in p.publish if r.platform != res.platform] + [res]
        storage.update(pid, save)
    if ok == 0 and p.brief.platforms:
        raise RuntimeError("Không đăng được lên nền tảng nào. Xem chi tiết lỗi ở bảng Đăng bài.")
    storage.set_status(pid, Status.PUBLISHED)


# ---------------- Sửa, chạy lại ----------------
def rerender_shot(pid: str, scene_id: int, new_prompt: str = "", new_source: Optional[str] = None) -> None:
    """Render lại 1 shot (seed mới, prompt/nguồn mới nếu có) rồi dựng lại video."""
    def prep(p: Project):
        p.status = Status.RENDERING
        r = next(r for r in p.renders if r.scene_id == scene_id)
        r.seed, r.status, r.error, r.file = random.randint(1, 2**31 - 1), "pending", None, None
        shot = next(s for s in p.shot_list.shots if s.scene_id == scene_id)
        if new_prompt.strip():
            shot.prompt = new_prompt.strip()
        if new_source in ("ai_video", "ai_image", "stock"):
            shot.source = new_source
        p.qa = None
    storage.update(pid, prep)
    _bg(produce, pid)


def resume(pid: str) -> None:
    """Tiếp tục từ bước đang dở (sau lỗi hoặc khởi động lại)."""
    p = storage.load(pid)
    approved = p.script_approved or p.shot_list is not None
    if not p.script:
        _bg(auto_flow if p.brief.topic == AUTO_PLACEHOLDER else write_flow, pid, *([] if p.brief.topic == AUTO_PLACEHOLDER else [""]))
    elif not approved:
        storage.set_status(pid, Status.REVIEW_SCRIPT)
    elif any(r.platform for r in p.publish if r.status in ("running", "failed")) and p.final_file and p.metadata:
        _bg(publish_flow, pid)
    else:
        storage.update(pid, lambda x: setattr(x, "script_approved", True))
        _bg(produce, pid)


def recover_interrupted() -> None:
    """Gọi khi khởi động: dự án đang chạy dở (do tắt máy) chuyển sang Lỗi để bấm Tiếp tục."""
    for p in storage.list_all():
        if p.status in BUSY:
            def f(x: Project):
                x.status = Status.FAILED
                x.error = "Bị gián đoạn do ứng dụng khởi động lại. Bấm 'Tiếp tục' để chạy tiếp."
            storage.update(p.id, f)
