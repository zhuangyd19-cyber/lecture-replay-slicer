#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载视频：优先 yt-dlp 直连；不支持的平台给出 m3u8 手动捕获指引。

用法：
  python3 download_video.py <URL> [-o 输出.mp4]
  python3 download_video.py --m3u8 <m3u8地址> [-o 输出.mp4] [--referer URL]

两种来源必须且只能给一个；输出文件已存在时默认拒绝覆盖（--force 除外）。
注意：只下载用户本人已获授权观看的内容（如自己报名课程的回放），勿用于传播。
"""
import argparse, os, shutil, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--m3u8", help="已抓取的 m3u8 直链（绕过 yt-dlp）")
    ap.add_argument("--referer", default=None, help="部分 CDN 校验 Referer 时需要")
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在的输出文件")
    ap.add_argument("-o", "--output", default="video.mp4")
    args = ap.parse_args()

    if bool(args.url) == bool(args.m3u8):
        ap.error("URL 和 --m3u8 必须且只能给一个")
    if os.path.exists(args.output) and not args.force:
        sys.exit(f"{args.output} 已存在，拒绝覆盖（确认要重下请加 --force）")

    if args.m3u8:
        cmd = ["ffmpeg", "-v", "warning"]
        if args.referer:
            cmd += ["-referer", args.referer]
        # 不加 -bsf:a aac_adtstoasc：对 AC-3 等非 AAC 音轨会直接失败；ffmpeg 封装 mp4 时自动处理 AAC
        cmd += ["-i", args.m3u8, "-c", "copy", "-y" if args.force else "-n", args.output]
        subprocess.run(cmd, check=True)
        print(f"OK → {args.output}")
        return

    if shutil.which("yt-dlp"):
        # --print after_move:filepath 拿到真实落盘路径（格式可能与扩展名不符，如 webm）
        r = subprocess.run(["yt-dlp", "--no-playlist", "--print", "after_move:filepath",
                            "--merge-output-format", "mp4", "-o", args.output, args.url],
                           capture_output=True, text=True)
        real = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
        if r.returncode == 0:
            if real and real != args.output:
                print(f"注意：实际落盘为 {real}（与 -o 指定名不同，格式已被 yt-dlp 校正）")
            print(f"OK → {real or args.output}")
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
