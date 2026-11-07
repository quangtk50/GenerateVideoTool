"""Bước 8 - Dựng video bằng FFmpeg.

1. Chuẩn hoá từng cảnh về cùng kích thước/fps, đúng thời lượng (video: cắt/kéo dài; ảnh: hiệu ứng Ken Burns).
2. Nối các cảnh.
3. Ghép lời thoại từng cảnh thành 1 track, đặt đúng vị trí.
4. Phụ đề ASS (tô màu từng từ), logo, nhạc nền tự giảm khi có lời (ducking), chuẩn hoá âm lượng -14 LUFS.
"""
from pathlib import Path
from typing import Dict

from . import config
from .ffutil import ffmpeg
from .schemas import Project
from .subtitles import build_ass

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _crf(h: int) -> int:
    return 20 if h >= 1900 else (21 if h >= 1200 else 24)


def scene_clip(src: Path, dst: Path, seconds: float, w: int, h: int, fps: int, crf: int,
               index: int, total: int) -> None:
    fades = []
    if index == 0:
        fades.append("fade=t=in:st=0:d=0.25")
    if index == total - 1:
        fades.append(f"fade=t=out:st={max(seconds - 0.5, 0):.2f}:d=0.5")
    tail = ("," + ",".join(fades)) if fades else ""
    enc = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-r", str(fps), str(dst)]
    if src.suffix.lower() in IMAGE_EXTS:
        frames = max(1, int(round(seconds * fps)))
        z = f"1+0.12*on/{frames}" if index % 2 == 0 else f"1.12-0.12*on/{frames}"
        vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},"
              f"setsar=1{tail}")
        ffmpeg(["-i", str(src), "-vf", vf, "-frames:v", str(frames), *enc])
    else:
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              f"fps={fps},setsar=1,tpad=stop_mode=clone:stop_duration=30{tail}")
        ffmpeg(["-i", str(src), "-t", f"{seconds:.3f}", "-vf", vf, *enc])


def voice_track(p: Project, durations: Dict[int, float], workdir: Path, dst: Path) -> None:
    voice = {v.scene_id: v for v in p.voices}
    inputs, filters, labels = [], [], []
    for i, sc in enumerate(p.script.scenes):
        d = durations[sc.id]
        v = voice.get(sc.id)
        if v and v.file and (workdir / "voice" / v.file).exists():
            inputs += ["-i", str(workdir / "voice" / v.file)]
        else:
            inputs += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        filters.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                       f"apad,atrim=end={d:.3f},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[a{i}]")
    graph = ";".join(filters) + f";{''.join(labels)}concat=n={len(labels)}:v=0:a=1[out]"
    ffmpeg([*inputs, "-filter_complex", graph, "-map", "[out]", "-c:a", "pcm_s16le", str(dst)])


def assemble(p: Project, workdir: Path, music_file: Path = None, out_name: str = "final.mp4",
             log=print) -> Path:
    w, h = config.frame_size(p.brief.resolution)
    fps, crf = config.FPS, _crf(h)
    tmp = workdir / "tmp"
    tmp.mkdir(exist_ok=True)
    durations = p.scene_durations()
    renders = {r.scene_id: r for r in p.renders}
    scenes = p.script.scenes

    # 1-2. Từng cảnh -> nối
    names = []
    for i, sc in enumerate(scenes):
        src = workdir / renders[sc.id].file
        dst = tmp / f"scene_{sc.id:02d}.mp4"
        scene_clip(src, dst, durations[sc.id], w, h, fps, crf, i, len(scenes))
        names.append(dst.name)
    (tmp / "list.txt").write_text("".join(f"file '{n}'\n" for n in names), encoding="utf-8")
    ffmpeg(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "joined.mp4"], cwd=tmp)

    # 3. Lời thoại
    voice_track(p, durations, workdir, tmp / "voice.wav")

    # 4. Phụ đề + logo + nhạc + loudnorm (chạy trong thư mục tmp để tránh lỗi đường dẫn Windows)
    build_ass(p, durations, w, h, tmp / "subs.ass")
    total = sum(durations.values())
    out = (workdir / out_name).resolve()
    inputs = ["-i", "joined.mp4", "-i", "voice.wav"]
    idx = 2
    music_idx = logo_idx = None
    if music_file:
        inputs += ["-stream_loop", "-1", "-i", str(Path(music_file).resolve())]
        music_idx, idx = idx, idx + 1
    if config.LOGO_FILE.exists():
        inputs += ["-i", str(config.LOGO_FILE.resolve())]
        logo_idx = idx

    def build(with_subs: bool) -> list:
        v = "[0:v]ass=subs.ass[vs]" if with_subs else "[0:v]null[vs]"
        if logo_idx is not None:
            m = int(w * 0.04)
            v += (f";[{logo_idx}:v]scale={int(w * 0.18)}:-1,format=rgba,colorchannelmixer=aa=0.85[lg];"
                  f"[vs][lg]overlay=W-w-{m}:{m}[vout]")
        else:
            v += ";[vs]null[vout]"
        loud = f"loudnorm=I={config.TARGET_LUFS}:TP=-1.5:LRA=11"
        if music_idx is not None:
            a = (f"[1:a]asplit=2[vo][sc];"
                 f"[{music_idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume={config.MUSIC_VOLUME},"
                 f"afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5[mu];"
                 f"[mu][sc]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350[duck];"
                 f"[vo][duck]amix=inputs=2:duration=first:normalize=0,{loud},aresample=48000[aout]")
        else:
            a = f"[1:a]{loud},aresample=48000[aout]"
        return [*inputs, "-filter_complex", f"{v};{a}", "-map", "[vout]", "-map", "[aout]",
                "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", str(out)]

    try:
        ffmpeg(build(True), cwd=tmp)
    except RuntimeError as e:
        log(f"Không chèn được phụ đề (FFmpeg thiếu libass?), xuất bản không phụ đề. {str(e)[:200]}")
        ffmpeg(build(False), cwd=tmp)
    return out
