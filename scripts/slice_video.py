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

注意：流复制切点对齐到关键帧，实际起点可能比 t0 略早（秒级）；
需要帧级精确时加 --accurate 走重编码（慢，画质有代际损失）。

用法：
  python3 slice_video.py 视频.mp4 边界表.csv [--srt 字幕.srt] [--outdir cut] [--accurate]
"""
import argparse, csv, os, re, subprocess, sys

from transcribe_srt import fmt_ts, load_srt, save_srt, duration


def safe_name(n):
    return re.sub(r'[\\/:*?"<>|]', "_", n).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("table", help="边界表 CSV：name,start,end（秒）")
    ap.add_argument("--srt", default=None)
    ap.add_argument("--outdir", default="cut")
    ap.add_argument("--accurate", action="store_true", help="重编码切片（帧级精确，慢）")
    args = ap.parse_args()

    srt = args.srt or os.path.splitext(args.video)[0] + ".srt"
    cues = load_srt(srt) if os.path.exists(srt) else []
    if not cues:
        print(f"警告：{srt} 无字幕，将只切视频。", file=sys.stderr)
    os.makedirs(args.outdir, exist_ok=True)
    vd = duration(args.video)

    with open(args.table, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"name", "start", "end"} <= set(reader.fieldnames):
            sys.exit(f"边界表表头必须是 name,start,end，实际：{reader.fieldnames}")
        rows = list(reader)
    if not rows:
        sys.exit("边界表为空，未执行任何切片。")

    # 预检：非法行 + 清洗后重名 + 与已有文件冲突
    valid, seen = [], {}
    for i, r in enumerate(rows, 2):
        try:
            t0, t1 = float(r["start"]), float(r["end"])
        except (TypeError, ValueError):
            print(f"SKIP 第{i}行：start/end 不是数字：{r}", file=sys.stderr)
            continue
        name = safe_name(r["name"] or f"segment{i}")
        if not (0 <= t0 < t1 <= vd + 5):
            print(f"SKIP {name}：区间 [{t0},{t1}] 非法或超出视频时长 {int(vd)}", file=sys.stderr)
            continue
        if name in seen:
            sys.exit(f"清洗后重名冲突：{name!r}（第 {seen[name]} 行与第 {i} 行），请改名后重跑。")
        seen[name] = i
        valid.append((name, t0, t1))
    if not valid:
        sys.exit("没有有效行，未执行任何切片。")

    done, skipped = 0, 0
    for name, t0, t1 in valid:
        out = os.path.join(args.outdir, name + ".mp4")
        outsrt = os.path.join(args.outdir, name + ".srt")
        if os.path.exists(out):
            print(f"SKIP {name}：{out} 已存在（不覆盖，如需重切请先删除）", file=sys.stderr)
            skipped += 1
            continue

        # 1) 片段字幕（时间平移）
        seg = [[st - t0, en - t0, body] for st, en, body in cues if st < t1 and en > t0]
        for c in seg:
            c[0] = max(0.0, c[0]); c[1] = min(t1 - t0, c[1])
        if seg:
            save_srt(outsrt, seg)

        # 2) 切片 + 内嵌字幕
        # -map 要点：0:V 主视频、0:a? 音轨（可无）、1:s:0 新字幕轨；
        # 绝不要 -map 0（会把输入里已有字幕轨再叠一份，每次重灌多一条）
        tmp = out + ".tmp.mp4"
        cmd = ["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", args.video]
        if seg:
            cmd += ["-i", outsrt]
        cmd += ["-map", "0:V:0", "-map", "0:a?"]
        if seg:
            cmd += ["-map", "1:s:0", "-metadata:s:s:0", "language=chi"]
        if args.accurate:
            cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac"]
            if seg:
                cmd += ["-c:s", "mov_text"]
        else:
            cmd += ["-c", "copy"]
            if seg:
                cmd += ["-c:s", "mov_text"]
        cmd += ["-y", tmp]
        subprocess.run(cmd, check=True)
        os.replace(tmp, out)
        done += 1
        print(f"OK {name}  {int(t1 - t0)}s  字幕 {len(seg)} 条", flush=True)

    print(f"SLICE DONE 成功 {done} 个，跳过 {skipped} 个，共 {len(valid)} 个有效段", flush=True)


if __name__ == "__main__":
    main()
