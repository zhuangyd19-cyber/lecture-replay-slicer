#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载视频：优先 yt-dlp 直连；不支持的平台给出 m3u8 手动捕获指引。

用法：
  python download_video.py <URL> [-o 输出.mp4]
  python download_video.py --m3u8 <m3u8地址> [-o 输出.mp4] [--referer URL]

注意：只下载用户本人已获授权观看的内容（如自己报名课程的回放），勿用于传播。
"""
import argparse, shutil, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--m3u8", help="已抓取的 m3u8 直链（绕过 yt-dlp）")
    ap.add_argument("--referer", default=None, help="部分 CDN 校验 Referer 时需要")
    ap.add_argument("-o", "--output", default="video.mp4")
    args = ap.parse_args()

    if args.m3u8:
        cmd = ["ffmpeg", "-v", "warning"]
        if args.referer:
            cmd += ["-referer", args.referer]
        cmd += ["-i", args.m3u8, "-c", "copy", "-bsf:a", "aac_adtstoasc", "-y", args.output]
        subprocess.run(cmd, check=True)
        print(f"OK → {args.output}")
        return

    if not args.url:
        ap.error("需要 URL 或 --m3u8")

    if shutil.which("yt-dlp"):
        r = subprocess.run(["yt-dlp", "--no-playlist", "-o", args.output, args.url])
        if r.returncode == 0:
            print(f"OK → {args.output}")
            return
        print("yt-dlp 不支持该站点或需登录态。", file=sys.stderr)
    else:
        print("未安装 yt-dlp（brew install yt-dlp）。", file=sys.stderr)

    print(__doc__, file=sys.stderr)
    print("手动捕获流程见 references/download-sources.md：用浏览器开发者工具抓 m3u8 后 "
          "重跑本脚本 --m3u8。", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
