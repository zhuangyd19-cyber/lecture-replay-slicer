#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""字幕对齐校验：每 N 秒从视频取音频重新识别，与 srt 在 ±150s 滑窗内模糊匹配。

输出每个采样点的 相似度 + 最佳偏移（正=字幕比声音晚）：
- 相似度 < 0.4 → ⚠️（疑似内容缺失/错位，但需分诊：无人声段新鲜识别会产生幻觉签名，属正常）
- 偏移绝对值 > 25s 且连续出现 → 该时段字幕漂移，用 transcribe_srt.py --replace-range 修复

用法：
  python align_check.py 视频.mp4 [字幕.srt] [--step 300] [--lang zh]
"""
import argparse, difflib, os, re, subprocess, tempfile

from transcribe_srt import HALLUC, asr_window, load_srt, norm_text, duration


def srt_window(cues, t0, t1):
    return "".join(norm_text(c[2]) for c in cues if c[0] < t1 and c[1] > t0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("srt", nargs="?", default=None)
    ap.add_argument("--step", type=float, default=300)
    ap.add_argument("--lang", default="zh")
    args = ap.parse_args()

    srt = args.srt or os.path.splitext(args.video)[0] + ".srt"
    cues = load_srt(srt)
    d = duration(args.video)
    print(f"{args.video}  时长 {int(d)}s  字幕 {len(cues)} 条  采样间隔 {int(args.step)}s", flush=True)

    bad = 0
    t = 120.0
    while t < d - 30:
        wav = tempfile.mktemp(suffix=".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-t", "12", "-i", args.video,
                        "-ar", "16000", "-ac", "1", "-y", wav], check=True)
        try:
            segs = asr_window(wav, args.lang)
        finally:
            os.unlink(wav)
        raw = "".join(s[2] for s in segs)
        a = norm_text(raw)
        if len(a) < 8 or any(h in a.lower() or h in a for h in HALLUC):
            print(f"  @{int(t):6d}s (无人声/幻觉，跳过)", flush=True)
            t += args.step
            continue
        best_r, best_off = 0.0, 0
        for off in range(-150, 151, 10):
            s = srt_window(cues, t + off, t + off + 12 + len(a) // 4)
            if not s:
                continue
            r = difflib.SequenceMatcher(None, a, s).ratio()
            if r > best_r:
                best_r, best_off = r, off
        mark = "⚠️" if best_r < 0.4 else ("⚠偏移" if abs(best_off) > 25 else "")
        if mark:
            bad += 1
        print(f"  @{int(t):6d}s 匹配 {best_r:.0%}  偏移 {best_off:+4d}s {mark}", flush=True)
        t += args.step
    print(f"CHECK DONE，异常点 {bad} 个", flush=True)


if __name__ == "__main__":
    main()
