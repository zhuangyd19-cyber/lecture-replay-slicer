#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按边界表把整场字幕拆成每段的纯文本逐字稿（供后续生成 Word/总结/脑图/PPT 备注）。

用法：
  python3 make_seg_docs.py 整场字幕.srt 边界表.csv [--outdir docs]

注意：srt 必须是整场视频时间轴的那份（transcribe_srt.py 的输出），
不是切片后从 0 起算的片段 srt。

输出：docs/<name>.txt —— 该段时间轴内的字幕正文，按句末标点成段。
总结、脑图、Word、PPT 的生成流程见 references/deliverables.md。
"""
import argparse, csv, math, os, re, sys

from transcribe_srt import load_srt


def safe_name(n):
    return re.sub(r'[\\/:*?"<>|]', "_", n).strip()


def join_cues(cues):
    """字幕条拼接：中文直接连；两侧都是英文字母时补空格，防止 neural+network 粘连。"""
    out = ""
    for _, _, body in cues:
        t = body.replace("\n", "").strip()
        if not t:
            continue
        if out and re.search(r"[A-Za-z]$", out) and re.match(r"^[A-Za-z]", t):
            out += " "
        out += t
    return out


def paragraphs(text):
    """按句末标点切段，约 150 字一段（在累计文本上切，不依赖字幕条边界）。"""
    sents = re.split(r"(?<=[。！？；])", text)
    out, buf = [], ""
    for s in sents:
        buf += s
        if len(buf) >= 150:
            out.append(buf); buf = ""
    if buf.strip():
        out.append(buf)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srt", help="整场视频时间轴的字幕")
    ap.add_argument("table", help="边界表 CSV：name,start,end（秒）")
    ap.add_argument("--outdir", default="docs")
    args = ap.parse_args()

    cues = load_srt(args.srt)
    if not cues:
        sys.exit(f"{args.srt} 没有字幕条目")
    os.makedirs(args.outdir, exist_ok=True)

    with open(args.table, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fn = reader.fieldnames or []
        if len(set(fn)) != len(fn):
            sys.exit(f"边界表存在重复列名：{fn}")
        if not {"name", "start", "end"} <= set(fn):
            sys.exit(f"边界表表头必须是 name,start,end，实际：{fn}")
        rows = list(reader)
    if not rows:
        sys.exit("边界表为空。")

    # 预检：区间合法 + 清洗后重名
    valid, seen = [], {}
    for i, r in enumerate(rows, 2):
        try:
            t0, t1 = float(r["start"]), float(r["end"])
        except (TypeError, ValueError):
            print(f"SKIP 第{i}行：start/end 不是数字：{r}", file=sys.stderr)
            continue
        name = safe_name(r["name"] or f"segment{i}")
        if not (math.isfinite(t0) and math.isfinite(t1) and 0 <= t0 < t1):
            print(f"SKIP {name}：非法区间 [{r['start']},{r['end']}]", file=sys.stderr)
            continue
        if name in seen:
            sys.exit(f"清洗后重名冲突：{name!r}（第 {seen[name]} 行与第 {i} 行），请改名后重跑。")
        seen[name] = i
        valid.append((name, t0, t1))
    if not valid:
        sys.exit("没有有效行。")

    done = 0
    for name, t0, t1 in valid:
        seg = [c for c in cues if c[0] < t1 and c[1] > t0]
        if not seg:
            print(f"SKIP {name}：区间内无字幕", file=sys.stderr)
            continue
        out = os.path.join(args.outdir, name + ".txt")
        ps = paragraphs(join_cues(seg))
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n\n".join(ps) + "\n")
        done += 1
        print(f"OK {name}  {sum(len(p) for p in ps)} 字 {len(ps)} 段", flush=True)
    print(f"DOCS DONE 成功 {done}/{len(valid)}", flush=True)
    if done == 0:
        sys.exit("零产出，请检查 srt 时间轴与边界表是否匹配（srt 必须是整场时间轴）。")


if __name__ == "__main__":
    main()
