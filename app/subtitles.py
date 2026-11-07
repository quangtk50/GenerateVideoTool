"""Phụ đề kiểu TikTok (ASS, tô màu từng từ theo giọng đọc)."""
import re
from pathlib import Path
from typing import Dict, List

from . import config
from .schemas import Project


def _ass_time(t: float) -> str:
    cs = int(round(max(t, 0) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _proportional(text: str, total: float) -> List[List]:
    """Không có mốc thời gian từ TTS -> chia thời gian theo độ dài từng từ."""
    words = text.split()
    if not words:
        return []
    weights = [len(w) + 2 for w in words]
    unit = total / sum(weights)
    out, t = [], 0.0
    for w, wt in zip(words, weights):
        out.append([t, t + wt * unit, w])
        t += wt * unit
    return out


def _attach_punct(timed: List[List], text: str) -> List[List]:
    """Edge TTS bỏ dấu câu trong mốc thời gian; lấy lại từ gốc trong voiceover nếu số từ khớp."""
    orig = text.split()
    if len(orig) == len(timed):
        return [[s, e, o] for (s, e, _), o in zip(timed, orig)]
    return timed


def _chunks(words: List[List], n: int) -> List[List[List]]:
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or re.search(r"[.,!?;:…]$", w[2]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def _esc(s: str) -> str:
    return s.replace("\\", "").replace("{", "(").replace("}", ")")


def build_ass(p: Project, durations: Dict[int, float], w: int, h: int, path: Path) -> None:
    voice = {v.scene_id: v for v in p.voices}
    size = int(h * 0.048)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.SUB_FONT},{size},&H0000E5FF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{max(2, size // 12)},1,2,{int(w * 0.08)},{int(w * 0.08)},{int(h * 0.2)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines, offset = [], 0.0
    for sc in p.script.scenes:
        dur = durations[sc.id]
        v = voice.get(sc.id)
        text = (v.text if v and v.text else sc.voiceover).strip()
        if text:
            if v and v.words:
                timed = _attach_punct(v.words, text)
            else:
                spoken = v.duration if v and v.duration else dur - 0.2
                timed = _proportional(text, max(spoken, 0.5))
            chunks = _chunks(timed, config.SUB_WORDS_PER_LINE)
            for i, ch in enumerate(chunks):
                start = ch[0][0]
                end = chunks[i + 1][0][0] if i + 1 < len(chunks) else min(ch[-1][1] + 0.3, dur)
                parts, cursor = [], start
                for ws, we, word in ch:
                    k = max(1, int(round((we - cursor) * 100)))
                    parts.append(f"{{\\kf{k}}}{_esc(word)}")
                    cursor = we
                lines.append(f"Dialogue: 0,{_ass_time(offset + start)},{_ass_time(offset + max(end, start + 0.3))},"
                             f"Default,,0,0,0,,{' '.join(parts)}")
        offset += dur
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
