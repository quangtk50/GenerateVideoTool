"""Dòng lệnh: chạy không cần giao diện web (tiện cho cron, server, kiểm thử).

  python -m app.cli check                               kiểm tra cấu hình, FFmpeg, API key
  python -m app.cli run --topic "Chủ đề..."             tạo 1 video từ đầu đến cuối (tự duyệt)
  python -m app.cli run --auto --publish youtube,tiktok AI tự nghĩ ý tưởng, tạo và đăng
  python -m app.cli resume <project_id>                 chạy tiếp dự án đang dở
  python -m app.cli youtube-auth                        đăng nhập YouTube (lần đầu)
  python -m app.cli analytics                           lấy số liệu + cập nhật insights
"""
import argparse
import shutil
import subprocess
import sys

from . import config, pipeline, storage
from .schemas import Brief


def cmd_check(_):
    print("== Thư mục dữ liệu:", config.DATA_DIR)
    for name in (config.FFMPEG_BIN, config.FFPROBE_BIN):
        path = shutil.which(name)
        print(f"== {name}: {path or 'KHÔNG TÌM THẤY - cài FFmpeg trước'}")
    if shutil.which(config.FFMPEG_BIN):
        out = subprocess.run([config.FFMPEG_BIN, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        print("   libass (phụ đề):", "có" if " ass " in out else "KHÔNG")
    print("== Module:")
    for k, v in config.status_summary().items():
        print(f"   {k:<18} {'THẬT' if v else 'giả lập / tắt'}")
    music = list(config.MUSIC_DIR.glob('*.*'))
    print(f"== Nhạc nền: {len(music)} file trong {config.MUSIC_DIR}")
    print(f"== Logo: {'có' if config.LOGO_FILE.exists() else 'không'} ({config.LOGO_FILE})")
    print(f"== YouTube token: {'có' if config.YOUTUBE_TOKEN.exists() else 'chưa (chạy youtube-auth)'}")


def cmd_run(a):
    platforms = [x.strip() for x in (a.publish or "").split(",") if x.strip()]
    brief = Brief(topic=a.topic or "", platform=a.platform, duration=a.duration, tone=a.tone,
                  audience=a.audience, resolution=a.resolution or config.DEFAULT_RESOLUTION,
                  visual_mode=a.visual, platforms=list(platforms),
                  auto_approve_script=True, auto_publish=False)
    if a.auto or not a.topic:
        p = pipeline.start_auto_project(brief, background=False)
        pipeline.auto_flow(p.id)
    else:
        p = pipeline.start_project(brief, background=False)
        pipeline.write_flow(p.id, "")
    p = storage.load(p.id)
    if platforms:
        pipeline.approve_publish(p.id, platforms, background=False)
        p = storage.load(p.id)
    d = storage.project_dir(p.id)
    print(f"\nXONG dự án {p.id} — trạng thái: {p.status.value}")
    print(f"Video: {d / p.final_file}")
    if p.qa:
        print(f"QA: {'đạt' if p.qa.passed else 'có lỗi'} — " + "; ".join(i.description for i in p.qa.issues))
    for r in p.publish:
        print(f"Đăng {r.platform}: {r.status} {r.url or r.error or ''}")


def cmd_resume(a):
    p = storage.load(a.project_id)
    if not p.script:
        pipeline.write_flow(p.id, "")
    else:
        storage.update(p.id, lambda x: setattr(x, "script_approved", True))
        pipeline.produce(p.id)
    print("Trạng thái:", storage.load(p.id).status.value)


def cmd_youtube_auth(_):
    from .publishers import youtube
    youtube.get_credentials(interactive=True)
    print("Đăng nhập YouTube thành công, token lưu ở", config.YOUTUBE_TOKEN)


def cmd_analytics(_):
    from . import analytics
    analytics.run()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m app.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    r = sub.add_parser("run")
    r.add_argument("--topic", default="")
    r.add_argument("--auto", action="store_true", help="AI tự nghĩ ý tưởng")
    r.add_argument("--platform", default="TikTok", help="nền tảng chính để viết kịch bản")
    r.add_argument("--duration", type=int, default=30)
    r.add_argument("--tone", default="cuốn hút, cảm xúc")
    r.add_argument("--audience", default="")
    r.add_argument("--resolution", default="")
    r.add_argument("--visual", default="auto", choices=["auto", "ai_video", "ai_image", "stock"])
    r.add_argument("--publish", default="", help="youtube,tiktok,facebook,instagram")
    r.set_defaults(fn=cmd_run)
    rs = sub.add_parser("resume")
    rs.add_argument("project_id")
    rs.set_defaults(fn=cmd_resume)
    sub.add_parser("youtube-auth").set_defaults(fn=cmd_youtube_auth)
    sub.add_parser("analytics").set_defaults(fn=cmd_analytics)
    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
