"""Lịch tự động (chạy trong cùng tiến trình web, không cần Redis/cron).

SCHEDULER_ENABLED=1
AUTO_TIMES=08:30,19:45      -> mỗi ngày tự tạo video ở các giờ này (AI tự nghĩ ý tưởng)
ANALYTICS_TIME=23:10        -> mỗi ngày lấy số liệu và cập nhật insights
"""
import threading
import time
from datetime import datetime

from . import analytics, config, pipeline
from .schemas import Brief

_fired = set()
_started = False


def auto_brief() -> Brief:
    return Brief(topic="", platform=config.AUTO_PLATFORM_LABEL, duration=config.AUTO_DURATION,
                 resolution=config.DEFAULT_RESOLUTION, platforms=list(config.DEFAULT_PLATFORMS),
                 auto_approve_script=config.AUTO_APPROVE_SCRIPT, auto_publish=config.AUTO_PUBLISH)


def _tick() -> None:
    now = datetime.now()
    hm, day = now.strftime("%H:%M"), now.strftime("%Y-%m-%d")
    for t in config.AUTO_TIMES:
        key = (day, "video", t)
        if hm == t and key not in _fired:
            _fired.add(key)
            p = pipeline.start_auto_project(auto_brief())
            print(f"[scheduler] {hm} tạo video tự động {p.id}")
    key = (day, "analytics")
    if hm == config.ANALYTICS_TIME and key not in _fired:
        _fired.add(key)
        threading.Thread(target=analytics.run, daemon=True).start()


def start() -> None:
    global _started
    if _started or not config.SCHEDULER_ENABLED:
        return
    _started = True

    def loop():
        while True:
            try:
                _tick()
            except Exception as e:  # noqa: BLE001
                print(f"[scheduler] lỗi: {e}")
            time.sleep(20)
    threading.Thread(target=loop, daemon=True, name="scheduler").start()
    print(f"[scheduler] bật: tạo video lúc {config.AUTO_TIMES}, thống kê lúc {config.ANALYTICS_TIME}")
