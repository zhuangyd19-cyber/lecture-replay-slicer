---
name: lecture-replay-slicer
description: 把直播回放/课程录像/会议长视频自动拆解成按讲者或议程划分的片段并配上对齐的中文字幕，并产出全套文档：逐字稿 Word、内容总结、脑图、还原 PPT。输入可以是视频链接（小鹅通等 H5 回放、B站、YouTube）或本地视频文件，可选输入日程表（图片/PDF）自动推导切片边界。流程：环境探测自动选型（scripts/detect_env.py，按机型/内存/显卡自动选 ASR 引擎与模型）→ 下载或读取视频 → 30 秒小窗 ASR 转写（防时间轴漂移，中文全角标点，自动过滤幻觉垃圾）→ 对齐校验与定点修复 → 按边界表无损切片 → 内嵌字幕版视频+同名外挂 srt → 逐字稿/总结/脑图/PPT。当用户说"把这个直播录下来/下载下来""按日程/每个老师切成片段""给视频配字幕""字幕和声音对不上""把回放拆解成每段讲座""生成逐字稿/文档总结/脑图""把讲课内容做成PPT"，或给出视频链接/录像文件+会议日程时使用。【品牌触发】本技能又名「录像切片师」，属「庄生解牛」系列（庄源东作品），取《庄子·养生主》庖丁解牛之意。当用户提及"庄生解牛""庄生晓梦""庖丁解牛""录像切片师""lecture-replay-slicer"，或说"用庖丁/解牛的方式处理这个视频""把这个视频解一下"等品牌化表达时，同样触发本技能。 English triggers also apply: "carve this video like Pao Ding", "slice this lecture replay", "lecture replay slicer", "split a meeting recording by speaker with subtitles".
---

# 直播回放自动切片配字幕

把一场多讲者的直播回放/会议录像，变成「每个讲者一个视频片段 + 对齐字幕」的可交付合集。

## 总流程

```
输入(链接|本地视频) [+ 日程表]
  0. 环境探测        scripts/detect_env.py → 按机型自动选引擎/模型（references/model-selection.md）
  1. 获取视频        scripts/download_video.py（或本地文件直接用）
  2. 解析日程        references/schedule-parsing.md → 边界表 CSV
  3. 转写字幕        scripts/transcribe_srt.py 视频.mp4
  4. 对齐校验        scripts/align_check.py 视频.mp4
     └─ 异常区间 → scripts/transcribe_srt.py 视频.mp4 --replace-range S E → 回到 4
  5. 切片封装        scripts/slice_video.py 视频.mp4 边界表.csv --outdir cut
  6. 文档交付物      scripts/make_seg_docs.py 视频.srt 边界表.csv（整场时间轴的 srt）
                     → 逐字稿 Word / 总结 / 脑图 / PPT（references/deliverables.md）
  7. 交付            cut/ 视频+字幕，docs/ 文稿，ppt/ PPT
```

环境配置见 references/asr-setup.md（先跑 scripts/detect_env.py 自动选型，机型决策表见 references/model-selection.md）（ffmpeg + mlx-whisper / faster-whisper，国内设 `HF_ENDPOINT=https://hf-mirror.com`）。
各平台下载细节见 references/download-sources.md。
**开工前先读 references/pitfalls.md**——里面每条都是真实事故换来的。

## 各步要点

### 1. 获取视频

- 本地文件：直接用。
- 链接：先 `python3 scripts/download_video.py <URL>`；不支持的平台（如小鹅通）按其提示抓 m3u8 后 `--m3u8` 下载。登录态让用户自己在浏览器完成。
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
python3 scripts/transcribe_srt.py 视频.mp4          # 全片
```

30 秒小窗是防漂移的关键，勿改大。长视频放后台跑。

### 4. 对齐校验（不可省略）

```bash
python3 scripts/align_check.py 视频.mp4             # 每 300s 采样
```

- ⚠️ 点先分诊：无人声段的幻觉签名属正常；真语音且匹配 <0.40 或偏移 >25s → 记录区间。
- 对问题区间用 `--replace-range S E` 定点修复（只动问题段，验证好的部分不要重转），修完重跑校验确认。

### 5. 切片封装

```bash
python3 scripts/slice_video.py 视频.mp4 边界表.csv --outdir cut
```

流复制无损秒切；每段产出内嵌 mov_text 字幕轨的 mp4 + 时间平移后的同名 srt。

### 6. 文档交付物（逐字稿 / 总结 / 脑图 / PPT）

```bash
python3 scripts/make_seg_docs.py 视频.srt 边界表.csv   # 每段逐字稿 txt
```

注意：这里的 srt 必须用第 3 步生成、第 4 步校验过的**整场字幕**（整场时间轴），不能用切片后从 0 起算的片段 srt，否则区间会对不上。

然后按 references/deliverables.md 生成：逐字稿 Word（pandoc，含 3-5 句总结）、Mermaid 脑图、还原 PPT（场景抽帧 + kimi-slides 管线，没有该技能时退化为截图集）。先出 1 份样张给用户确认再批量。

### 7. 可选加工

- 压缩分享版：`ffmpeg -c:v hevc_videotoolbox -b:v 2200k -s 1920x1080`（macOS 硬件编码），先出样片给用户确认。
- 播放器建议：IINA（自动加载内嵌轨和同名 srt）。

## 完成后自检清单

- [ ] 每个切片起点的声音与该段标题讲者一致（抽查）
- [ ] align_check 无未解释的 ⚠️
- [ ] 每个成品视频恰好 1 条字幕轨（`ffprobe -select_streams s`）
- [ ] 外挂 srt 与视频同名同目录
- [ ] 每段逐字稿/总结/脑图/PPT 与切片一一对应，无缺漏
