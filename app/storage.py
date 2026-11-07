"""Lưu dự án dạng JSON: data/projects/<id>/project.json.
Đơn giản, dễ sao lưu; muốn nhiều máy chủ cùng chạy thì chuyển sang PostgreSQL (xem docs/KIEN_TRUC.md)."""
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, List

from . import config
from .schemas import Brief, Project, Status

_lock = threading.RLock()


def project_dir(pid: str) -> Path:
    d = config.DATA_DIR / pid
    d.mkdir(parents=True, exist_ok=True)
    return d


def create(brief: Brief, status: Status = Status.WRITING) -> Project:
    pid = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    p = Project(id=pid, created_at=datetime.now().isoformat(timespec="seconds"),
                brief=brief, status=status)
    save(p)
    return p


def save(p: Project) -> None:
    with _lock:
        path = project_dir(p.id) / "project.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(p.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)


def load(pid: str) -> Project:
    with _lock:
        f = config.DATA_DIR / pid / "project.json"
        return Project.model_validate_json(f.read_text(encoding="utf-8"))


def update(pid: str, fn: Callable[[Project], None]) -> Project:
    """Đọc - sửa - ghi an toàn giữa nhiều thread."""
    with _lock:
        p = load(pid)
        fn(p)
        save(p)
        return p


def set_status(pid: str, status: Status) -> None:
    def f(p: Project):
        p.status = status
        if status != Status.FAILED:
            p.error = None
    update(pid, f)


def log(pid: str, msg: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    update(pid, lambda p: p.log.append(f"[{stamp}] {msg}"))


def list_all() -> List[Project]:
    out = []
    for d in sorted(config.DATA_DIR.iterdir(), reverse=True):
        if (d / "project.json").exists():
            try:
                out.append(load(d.name))
            except Exception:  # noqa: BLE001 - bỏ qua file hỏng
                pass
    return out
