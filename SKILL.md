---
name: lecture-replay-slicer
description: 把直播回放/课程录像/会议长视频自动拆解成按讲者或议程划分的片段并配上对齐的中文字幕。输入可以是视频链接（小鹅通等 H5 回放、B站、YouTube）或本地视频文件，可选输入日程表（图片/PDF）自动推导切片边界。流程：下载或读取视频 → 30 秒小窗 ASR 转写（防时间轴漂移，中文全角标点，自动过滤幻觉垃圾）→ 对齐校验与定点修复 → 按边界表无损切片 → 生成内嵌字幕版视频+同名外挂 srt。当用户说"把这个直播录下来/下载下来""按日程/每个老师切成片段""给视频配字幕""字幕和声音对不上""把回放拆解成每段讲座"，或给出视频链接/录像文件+会议日程时使用。
---

# 直播回放自动切片配字幕

把一场多讲者的直播回放/会议录像，变成「每个讲者一个视频片段 + 对齐字幕」的可交付合集。

## 总流程

```
输入(链接|本地视频) [+ 日程表]
  1. 获取视频        scripts/download_video.py（或本地文件直接用）
  2. 解析日程        references/schedule-parsing.md → 边界表 CSV
  3. 转写字幕        scripts/transcribe_srt.py 视频.mp4
  4. 对齐校验        scripts/align_check.py 视频.mp4
     └─ 异常区间 → scripts/transcribe_srt.py 视频.mp4 --replace-range S E → 回到 4
  5. 切片封装        scripts/slice_video.py 视频.mp4 边界表.csv --outdir cut
  6. 交付            cut/ 下每段 mp4（内嵌字幕轨）+ 同名 srt（外挂）
```

环境配置见 references/asr-setup.md（ffmpeg + mlx-whisper / faster-whisper，国内设 `HF_ENDPOINT=https://hf-mirror.com`）。
各平台下载细节见 references/download-sources.md。
**开工前先读 references/pitfalls.md**——里面每条都是真实事故换来的。

## 各步要点

### 1. 获取视频

- 本地文件：直接用。
- 链接：先 `scripts/download_video.py <URL>`；不支持的平台（如小鹅通）按其提示抓 m3u8 后 `--m3u8` 下载。登录态让用户自己在浏览器完成。
- 只处理用户已获授权观看的内容。

### 2. 解析日程 → 边界表

日程是墙钟、视频是偏移，必须定锚点对齐（references/schedule-parsing.md）。边界表为 CSV：

```csv
name,start,end
01-开幕式,1790,2540
02-张三-混合式教学设计,2660,4520
```

没有日程时退化为语义切片：用转写文本找"下面有请/我是来自/感谢…的精彩分享"等切换点，每段命名后请用户确认。

### 3. 转写

```bash
python scripts/transcribe_srt.py 视频.mp4          # 全片
```

30 秒小窗是防漂移的关键，勿改大。长视频放后台跑。

### 4. 对齐校验（不可省略）

```bash
python scripts/align_check.py 视频.mp4             # 每 300s 采样
```

- ⚠️ 点先分诊：无人声段的幻觉签名属正常；真语音且匹配 <0.35 或偏移 >25s → 记录区间。
- 对问题区间用 `--replace-range S E` 定点修复（只动问题段，验证好的部分不要重转），修完重跑校验确认。

### 5. 切片封装

```bash
python scripts/slice_video.py 视频.mp4 边界表.csv --outdir cut
```

流复制无损秒切；每段产出内嵌 mov_text 字幕轨的 mp4 + 时间平移后的同名 srt。

### 6. 可选交付物

- 逐字稿 Word：按边界表把 srt 文本切段，LLM 顺句读补标点后转 docx。
- 压缩分享版：`ffmpeg -c:v hevc_videotoolbox -b:v 2200k -s 1920x1080`（macOS 硬件编码），先出样片给用户确认。
- 播放器建议：IINA（自动加载内嵌轨和同名 srt）。

## 完成后自检清单

- [ ] 每个切片起点的声音与该段标题讲者一致（抽查）
- [ ] align_check 无未解释的 ⚠️
- [ ] 每个成品视频恰好 1 条字幕轨（`ffprobe -select_streams s`）
- [ ] 外挂 srt 与视频同名同目录
