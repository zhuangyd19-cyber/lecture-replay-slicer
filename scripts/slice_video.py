#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按边界表把长视频切成片段，并生成同步字幕（外挂 srt + 内嵌 mov_text）。

边界表 CSV（逗号分隔，UTF-8，含表头）：
  name,start,end
  01-开幕式,1790,2540
  02-张三-混合式教学设计,2660,4520
起止单位是秒（视频内偏移，不是墙钟时间——怎么从日程表得到偏移见 references/schedule-parsing.md）。

对每个片段输出（到 --outdir）：
  <name>.mp4   无损流复制切片（不重编码，秒级完成），内嵌一条中文字幕轨
  <name>.srt   时间轴已平移到片段起点的同名外挂字幕（播放器自动加载）

用法：
  python slice_video.py 视频.mp4 边界表.csv [--srt 字幕.srt] [--outdir cut]
"""
import argparse, csv, os, re, subprocess

from transcribe_srt import fmt_ts, load_srt, save_srt, duration


def safe_name(n):
    return re.sub(r'[\\/:*?"<>|]', "_", n).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("table", help="边界表 CSV：name,start,end（秒）")
    ap.add_argument("--srt", default=None)
    ap.add_argument("--outdir", default="cut")
    args = ap.parse_args()

    srt = args.srt or os.path.splitext(args.video)[0] + ".srt"
    cues = load_srt(srt) if os.path.exists(srt) else []
    os.makedirs(args.outdir, exist_ok=True)
    vd = duration(args.video)

    with open(args.table, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r.get("name")]

    for r in rows:
        name = safe_name(r["name"])
        t0, t1 = float(r["start"]), float(r["end"])
        if t1 > vd + 5:
            print(f"SKIP {name}：end {t1} 超出视频时长 {int(vd)}")
            continue
        out = os.path.join(args.outdir, name + ".mp4")
        outsrt = os.path.join(args.outdir, name + ".srt")

        # 1) 片段字幕（时间平移）
        seg = [[st - t0, en - t0, body] for st, en, body in cues if st < t1 and en > t0]
        for c in seg:
            c[0] = max(0.0, c[0]); c[1] = min(t1 - t0, c[1])
        if seg:
            save_srt(outsrt, seg)

        # 2) 无损切片 + 内嵌字幕
        # 注意 -map 写法：0:v 0:a 加新字幕轨；绝对不要 -map 0（会把已有字幕轨再叠一份）
        cmd = ["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", args.video]
        if seg:
            cmd += ["-i", outsrt, "-map", "0:v", "-map", "0:a", "-map", "1",
                    "-c", "copy", "-c:s", "mov_text", "-metadata:s:s:0", "language=chi"]
        else:
            cmd += ["-map", "0:v", "-map", "0:a", "-c", "copy"]
        cmd += ["-y", out]
        subprocess.run(cmd, check=True)
        print(f"OK {name}  {int(t1 - t0)}s  字幕 {len(seg)} 条", flush=True)

    print("SLICE DONE", flush=True)


if __name__ == "__main__":
    main()
