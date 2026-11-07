"""Kiểm thử trọn luồng ở chế độ giả lập (không tốn tiền, không cần mạng).
Chạy:  pytest -q
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_full_pipeline_mock(tmp_path):
    env = {**os.environ, "DATA_ROOT": str(tmp_path / "data"), "ASSETS_DIR": str(tmp_path / "assets"),
           "MOCK_CLAUDE": "1", "MOCK_SEEDANCE": "1", "MOCK_MEDIA": "1", "PUBLISH_DRY_RUN": "1",
           "DEFAULT_RESOLUTION": "480p", "PYTHONPATH": str(ROOT)}
    r = subprocess.run([sys.executable, "-m", "app.cli", "run", "--topic", "Kiểm thử", "--duration", "15",
                        "--publish", "youtube,tiktok"], cwd=ROOT, env=env, capture_output=True, text=True,
                       timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "published" in r.stdout
    videos = list((tmp_path / "data" / "projects").glob("*/final.mp4"))
    assert videos and videos[0].stat().st_size > 10_000
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                            str(videos[0])], capture_output=True, text=True).stdout
    assert "video" in probe and "audio" in probe
    assert (videos[0].parent / "thumbnail.jpg").exists()


def test_subtitle_chunks():
    sys.path.insert(0, str(ROOT))
    from app.subtitles import _chunks, _proportional
    words = _proportional("Một hai ba bốn năm, sáu bảy.", 3.0)
    assert abs(words[-1][1] - 3.0) < 1e-6
    chunks = _chunks(words, 4)
    assert [len(c) for c in chunks] == [4, 1, 2]
