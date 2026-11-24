#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频/音频 → 中文 SRT 字幕。

核心设计（来自实战教训）：
- 按 30 秒小窗转写。长音频整块转写会让 whisper 时间轴逐渐漂移（实测 10 分钟块尾可漂 40 秒），
  30 秒是 whisper 原生窗口，基本不漂移。
- 幻觉过滤：无人声段（掌声/音乐/静默）whisper 会输出"优优独播""请不吝点赞"等固定签名，必须过滤。
- 重复过滤：识别卡顿时会输出同一短句循环 N 遍，按重复子串检测删除。
- 全角标点：中文语境下的半角 , . ? ! ; : 统一转全角（数字/英文之间的不动）。

用法：
  python transcribe_srt.py 视频.mp4                        # 全片转写 → 同名 .srt
  python transcribe_srt.py 视频.mp4 --start 300 --end 900  # 只转写区间（仍会写完整 srt）
  python transcribe_srt.py 视频.mp4 --replace-range 7350 12651
      # 定点修复：删除现有同名 srt 中与该区间的重叠条目，用重新识别的结果替换（其余条目原样保留）

环境（详见 references/asr-setup.md）：
  Apple Silicon 优先 mlx-whisper（模型 mlx-community/whisper-large-v3-turbo）；
  其它平台回退 faster-whisper（large-v3-turbo 或 large-v3）。
  国内下载模型先设 HF_ENDPOINT=https://hf-mirror.com
"""
import argparse, os, re, subprocess, sys, tempfile

WIN = 30.0  # 转写窗口秒数，勿调大（漂移根因）

HALLUC = [
    "优优独播", "yoyo television", "请不吝点赞", "打赏支持", "明镜与点点",
    "字幕志愿者", "感谢大家收看", "感谢观看", "请订阅", "点点关注",
    "中文字幕志愿者", "bilibili", "点赞订阅",
]
PUNCT = {",": "，", ".": "。", "?": "？", "!": "！", ";": "；", ":": "："}


def norm_text(t):
    """去掉标点与空白，用于重复检测。"""
    return re.sub(r"[，。？！、；：,.?!;:\s—…·\"'\"'（）()《》【】]", "", t)


def is_junk(t):
    t = t.strip()
    if not t:
        return True
    low = t.lower()
    if any(h in low or h in t for h in HALLUC):
        return True
    n = norm_text(t)
    if len(n) < 2:
        return True
    # 任一 4/6/8 字子串重复 3 次以上 → 循环垃圾
    for L in (4, 6, 8):
        for i in range(0, max(1, len(n) - L * 3 + 1), 2):
            if n[i:i + L] and n.count(n[i:i + L]) >= 3:
                return True
    return False


def to_fullwidth(t):
    """中文语境半角标点转全角（相邻任一侧是 CJK 才转，数字间的逗号/小数点不动）。"""
    def repl(m):
        if m.group(2):
            return m.group(1) + PUNCT[m.group(2)]
        return PUNCT[m.group(3)] + m.group(4)
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"([一-鿿])([,.?!;:])|([,.?!;:])([一-鿿])", repl, t)
    return t


def fmt_ts(sec):
    ms = max(0, int(round(sec * 1000)))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


SRT_RE = re.compile(r"(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)")


def load_srt(path):
    cues = []
    if not os.path.exists(path):
        return cues
    txt = open(path, encoding="utf-8").read()
    for b in re.split(r"\n\s*\n", txt.strip()):
        m = SRT_RE.search(b)
        if not m:
            continue
        st = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) + int(m[4]) / 1000
        en = int(m[5]) * 3600 + int(m[6]) * 60 + int(m[7]) + int(m[8]) / 1000
        body = "\n".join(l for l in b.split("\n") if "-->" not in l and not l.strip().isdigit()).strip()
        if body:
            cues.append([st, en, body])
    return cues


def save_srt(path, cues):
    cues.sort(key=lambda c: c[0])
    with open(path, "w", encoding="utf-8") as f:
        for i, (st, en, body) in enumerate(cues, 1):
            f.write(f"{i}\n{fmt_ts(st)} --> {fmt_ts(en)}\n{body}\n\n")


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())


# ---------- ASR 后端 ----------
_BACKEND = None


def _load_backend():
    global _BACKEND
    if _BACKEND:
        return _BACKEND
    try:
        import mlx_whisper  # Apple Silicon
        _BACKEND = ("mlx", mlx_whisper)
        return _BACKEND
    except ImportError:
        pass
    from faster_whisper import WhisperModel  # 其它平台
    model = WhisperModel("large-v3-turbo", device="auto", compute_type="auto")
    _BACKEND = ("faster", model)
    return _BACKEND


def asr_window(wav, lang="zh"):
    """识别单个短音频文件，返回 [(start, end, text), ...]（相对窗口起点）。"""
    kind, be = _load_backend()
    if kind == "mlx":
        r = be.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language=lang)
        return [(s["start"], s["end"], s["text"]) for s in r["segments"]]
    segs, _ = be.transcribe(wav, language=lang, vad_filter=True)
    return [(s.start, s.end, s.text) for s in segs]


def transcribe_range(video, t0, t1, lang="zh"):
    """按 30 秒小窗转写 [t0, t1]，返回绝对时间字幕条。"""
    cues = []
    w = t0
    total = max(1, int((t1 - t0) / WIN) + 1)
    done = 0
    while w < t1:
        ln = min(WIN, t1 - w)
        wav = tempfile.mktemp(suffix=".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(w), "-t", str(ln), "-i", video,
                        "-ar", "16000", "-ac", "1", "-y", wav], check=True)
        try:
            for st, en, text in asr_window(wav, lang):
                text = to_fullwidth(text.strip())
                if is_junk(text):
                    continue
                a, b = w + st, w + en
                if a >= t1 or b <= t0:
                    continue
                cues.append([a, min(b, t1), text])
        finally:
            os.unlink(wav)
        w += WIN
        done += 1
        if done % 20 == 0 or done == total:
            print(f"  转写进度 {done}/{total} 窗（{int(w)}s）", flush=True)
    return cues


def main():
    ap = argparse.ArgumentParser(description="视频 → 中文 SRT 字幕（30s 小窗防漂移）")
    ap.add_argument("video")
    ap.add_argument("-o", "--output", help="输出 srt 路径，默认同名 .srt")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--replace-range", type=float, nargs=2, metavar=("S", "E"),
                    help="定点修复模式：替换现有 srt 中 [S,E] 区间")
    args = ap.parse_args()

    srt = args.output or os.path.splitext(args.video)[0] + ".srt"
    d = duration(args.video)
    t0, t1 = args.start, (args.end if args.end is not None else d)

    if args.replace_range:
        r0, r1 = args.replace_range
        old = load_srt(srt)
        kept = [c for c in old if not (c[0] < r1 and c[1] > r0)]
        print(f"删除 [{r0}-{r1}] 内 {len(old) - len(kept)} 条", flush=True)
        new = transcribe_range(args.video, r0, r1, args.lang)
        save_srt(srt, kept + new)
        print(f"修复完成：{len(old)} -> {len(load_srt(srt))} 条（新增 {len(new)}）→ {srt}", flush=True)
    else:
        cues = transcribe_range(args.video, t0, t1, args.lang)
        save_srt(srt, cues)
        print(f"完成 {len(cues)} 条 → {srt}", flush=True)


if __name__ == "__main__":
    main()
