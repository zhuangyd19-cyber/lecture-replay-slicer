# 视频来源与下载

合规前提：只下载用户本人已获授权观看的内容（自己报名的课程回放、公开直播、自有素材），供个人学习存档，勿二次传播。

## 优先级

1. **本地文件** → 直接用，跳过下载。
2. **直链 / 常见站点**（B站、YouTube 等）→ `scripts/download_video.py <URL>`（走 yt-dlp）。
3. **小鹅通（xiaoeknow）等 H5 回放页** → yt-dlp 多半不支持，需抓 m3u8：

### 小鹅通回放抓取流程（实战验证）

页面形如 `https://<appid>.h5.xiaoeknow.com/v4/course/alive/l_<id>?...&type=2`（`type=2` 即回放）。

1. 让用户在自己的浏览器里打开回放页并登录（登录态在浏览器里，不要替用户输账号密码）。
2. 打开开发者工具 → Network → 过滤 `m3u8`，点播放，抓到形如
   `https://....cdn.../....m3u8?sign=...` 的地址，复制完整 URL。
3. `scripts/download_video.py --m3u8 "<地址>" -o 视频.mp4`；若 403，加 `--referer "回放页URL"`。
4. 多个分场/分论坛重复同样流程（同一课程的不同回放页结构一致，只是 `l_<id>` 不同）。

如果机器上有浏览器自动化能力（如 Kimi WebBridge），可由 Agent 代劳第 2 步的抓包，但登录必须用户自己完成。

### 备选：录屏

抓不到 m3u8 时兜底：macOS 自带 `screencapture -v` 或 QuickTime 录屏。代价是必须 1:1 实时录完，且画质受屏幕限制——能抓流就不用录屏。
