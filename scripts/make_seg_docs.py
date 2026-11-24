#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按边界表把整场字幕拆成每段的纯文本逐字稿（供后续生成 Word/总结/脑图/PPT 备注）。

用法：
  python3 make_seg_docs.py 字幕.srt 边界表.csv [--outdir docs]

输出：docs/<name>.txt —— 该段时间轴内的字幕正文，按语气成段。
总结、脑图、Word、PPT 的生成流程见 references/deliverables.md。
"""
import argparse, csv, os, re, sys

from transcribe_srt import load_srt


def safe_name(n):
    return re.sub(r'[\\/:*?"<>|]', "_", n).strip()


def paragraphs(cues):
    """字幕条 → 段落：以句末标点收段，约 150 字一段。"""
    buf, out = "", []
    for _, _, body in cues:
        t = body.replace("\n", "")
        buf += t
        if len(buf) >= 150 and re.search(r"[。！？；]$", t):
            out.append(buf); buf = ""
    if buf:
        out.append(buf)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt")
    ap.add_argument("table", help="边界表 CSV：name,start,end（秒）")
    ap.add_argument("--outdir", default="docs")
    args = ap.parse_args()

    cues = load_srt(args.srt)
    if not cues:
        sys.exit(f"{args.srt} 没有字幕条目")
    os.makedirs(args.outdir, exist_ok=True)

    with open(args.table, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"name", "start", "end"} <= set(reader.fieldnames):
            sys.exit(f"边界表表头必须是 name,start,end，实际：{reader.fieldnames}")
        rows = list(reader)

    for i, r in enumerate(rows, 2):
        try:
            t0, t1 = float(r["start"]), float(r["end"])
        except (TypeError, ValueError):
            print(f"SKIP 第{i}行：start/end 不是数字", file=sys.stderr)
            continue
        name = safe_name(r["name"] or f"segment{i}")
        seg = [c for c in cues if c[0] < t1 and c[1] > t0]
        if not seg:
            print(f"SKIP {name}：区间内无字幕", file=sys.stderr)
            continue
        out = os.path.join(args.outdir, name + ".txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n\n".join(paragraphs(seg)) + "\n")
        print(f"OK {name}  {sum(len(p) for p in paragraphs(seg))} 字", flush=True)
    print("DOCS DONE", flush=True)


if __name__ == "__main__":
    main()
