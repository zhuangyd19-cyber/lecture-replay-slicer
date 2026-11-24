# 每段交付物：逐字稿 Word、总结、脑图、PPT

前置：`make_seg_docs.py` 已把每段字幕切成 `docs/<name>.txt` 逐字稿（纯文本）。

## 逐字稿 Word（docs/docx/<name>.docx）

1. 通读 txt，按语义补全句读标点（，、。、？、！）并分段——ASR 文本按停顿断行，需要顺成文。
2. 保持原文，不改写观点；明显的 ASR 同音错字（人名、术语）结合上下文修正，拿不准的保留原样。
3. 每篇开头加标题（序号-讲者-题目）+ 3–5 句「内容总结」。
4. 转 Word：`pandoc in.md -o out.docx`（`brew install pandoc`）。

## 脑图（docs/mindmap/<name>.md）

用 Mermaid mindmap 语法生成，结构：根节点=讲者+题目，一级=报告主线（3–6 个），二级=关键论点/方法/案例，每节点 ≤15 字。
mermaid 代码放进 .md 代码块交付；有 mermaid-cli（`npm i -g @mermaid-js/mermaid-cli`）时再渲染 PNG，不装也能在 Typora/Obsidian/GitHub 直接看。

## PPT（ppt/<name>/）

把视频里讲者翻页的幻灯片还原成可编辑 PPT：

1. **抽帧**：先建目录再抽，保留首帧防止漏掉第一页：
   ```bash
   mkdir -p frames/<name> && ffmpeg -i 片段.mp4 -vf "select='eq(n,0)+gt(scene,0.35)',showinfo" -vsync vfr frames/<name>/%04d.png
   ```
   按场景切换抽帧，翻页瞬间会出一帧；同页停留久会重复，按视觉去重（PPT 内容不变的帧只留一张）。
   对变化小的翻页（同一模板只改几行字，场景分低于阈值），再用定时抽帧补查：`-vf fps=1/30` 抽样比对。
2. **还原**：有 kimi-slides 技能时走其 PPTD 管线（每页：截图作底或重排文字版式，备注写该页的逐字稿原文），逐页构建、校验、交付。
   没有该技能时退化为「截图集 + 逐字稿备注」的朴素 PPT 或直接交付图片集。
3. 页数失控时（>80 页）先问用户是否只要关键页。

## 交付顺序

逐字稿 Word → 总结 → 脑图 → PPT。前三样快（分钟级），PPT 最慢，放最后并先给 1 份样张确认风格。
