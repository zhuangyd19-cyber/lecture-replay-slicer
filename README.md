# 回放切片师（lecture-replay-slicer）

「庄生晓梦」系列 · 庄源东（zhuangyd19-cyber）作品

![海报](assets/poster.png)

> 庄生晓梦迷蝴蝶，庖丁解牛游刃有余——一场几小时的直播回放如同一场长梦，这个技能把它切成清晰的片段：「每位讲者一段视频 + 对齐字幕 + 逐字稿 + 总结 + 脑图 + 还原 PPT」的完整资料包。由庄源东（zhuangyd19-cyber）出品。

一个给 AI Agent（Kimi 等）使用的技能包（Skill）。你只需要给它**一个回放链接（或本地录像）+ 一张会议日程表**，剩下的全部自动完成。

## 效果

输入：

- 小鹅通等平台的直播回放链接，或本地视频文件
- 会议日程（图片 / PDF / 文字均可）

输出：

```
cut/        每位讲者的切片视频（内嵌字幕轨 + 同名外挂 srt，IINA/VLC 自动加载）
docs/       逐字稿 Word（含 3-5 句内容总结）
docs/mindmap/  每场报告的脑图（Mermaid 格式）
ppt/        从视频画面还原的可编辑 PPT
```

## 为什么需要它（而不是直接用 whisper + ffmpeg）

长视频转写有一堆看不见的坑，这个技能把我们踩过的坑全部变成了内置防线：

- **whisper 长时间轴漂移**：整块转写 10 分钟，字幕最多能比声音晚 40 秒。本技能强制 30 秒小窗转写，并附带「采样校验 → 漂移区间定点重识别」的完整修复闭环。
- **幻觉垃圾**：掌声/音乐/静默会被识别成"优优独播剧场""请不吝点赞"等固定签名，内置过滤。
- **音字不匹配难察觉**：`align_check.py` 每 5 分钟采样复听，输出每段偏移量，问题一目了然。
- **日程≠视频时间**：日程是墙钟，录像是偏移，技能里写了完整的锚点对齐方法。
- **ffmpeg 字幕轨叠加陷阱**、**无损切片关键帧偏移**、**英文单词粘连**……11 条实战教训都在 `references/pitfalls.md`。

## 工作流程

```
输入(链接|本地视频) [+ 日程表]
  1. 获取视频      download_video.py（yt-dlp / m3u8 抓流）
  2. 解析日程      → 边界表 CSV（讲者,起,止）
  3. 转写字幕      transcribe_srt.py（30s 小窗，全角标点，幻觉过滤）
  4. 对齐校验      align_check.py（异常区间用 --replace-range 定点修复）
  5. 切片封装      slice_video.py（无损流复制 + 双字幕）
  6. 文档交付物    make_seg_docs.py → 逐字稿 Word / 总结 / 脑图 / PPT
```

## 安装

把本目录放入你的 Agent 技能目录（如 Kimi 的 `skills/` 目录），或直接安装 `.skill` 分发包。

运行依赖：`ffmpeg`、Python 3.10+、ASR 后端二选一（Apple Silicon 装 `mlx-whisper`，其它平台装 `faster-whisper`；国内设 `HF_ENDPOINT=https://hf-mirror.com` 加速模型下载）。详见 `references/asr-setup.md`。

## 使用（对 Agent 说人话即可）

> "这是年会回放的 5 个链接和日程表，帮我下载下来，按每位老师切成片段，配上字幕，再生成逐字稿和 PPT。"

Agent 会自动加载本技能并执行完整流程。

## 目录结构

```
lecture-replay-slicer/
├── SKILL.md                    # 技能入口：触发条件 + 工作流
├── scripts/                    # 5 个可独立运行的脚本
│   ├── download_video.py       # 下载（yt-dlp / m3u8）
│   ├── transcribe_srt.py       # 转写 + 定点修复
│   ├── align_check.py          # 音字对齐校验
│   ├── slice_video.py          # 无损切片 + 字幕封装
│   └── make_seg_docs.py        # 逐字稿拆分
└── references/                 # 按需加载的详细文档
    ├── asr-setup.md            # ASR 环境配置
    ├── download-sources.md     # 各平台下载方法
    ├── schedule-parsing.md     # 日程表 → 边界表
    ├── deliverables.md         # Word/总结/脑图/PPT 生成
    └── pitfalls.md             # 实战踩坑清单
```

## 命名与典故

![庖丁解牛 · 胶片牛](assets/paoding-film-ox.png)

**庄生晓梦**——语出李商隐《锦瑟》：「庄生晓梦迷蝴蝶」。一场数小时的直播回放如同一场长梦，会后回想只剩混沌；本技能把梦切成清晰的片段，让内容醒来即可用。「庄」亦取自作者之姓。

**庖丁解牛**——语出《庄子·养生主》：「以无厚入有间，恢恢乎其于游刃必有余地矣。」这正是本技能工作方式的写照：

> 牛者，数小时之回放也；刃者，语音识别也；有间者，讲者之边界也。

七步工作流（下载 → 转写 → 标点 → 对齐 → 切片 → 成文 → 出课件），是谓「解牛七式」。

## 合规声明

本工具仅供处理**你本人已获授权观看**的内容（自己报名的课程回放、公开直播、自有素材），用于个人学习存档。请勿用于破解付费内容或二次传播。

## License

MIT
