# ASR 环境配置

## 依赖

- `ffmpeg` / `ffprobe`（macOS：`brew install ffmpeg`）
- Python 3.10+，建议为 ASR 建独立 venv：

```bash
python3 -m venv .venv-asr && source .venv-asr/bin/activate
```

## 后端选择（transcribe_srt.py 自动探测，按序回退）

1. **Apple Silicon（M 系列）首选 mlx-whisper**：
   ```bash
   pip install mlx-whisper
   ```
   模型 `mlx-community/whisper-large-v3-turbo`（约 1.6 GB），首次运行自动从 HuggingFace 下载。
   **国内网络**必须先设镜像，否则下载卡死：
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```
   模型只下一次，之后缓存于 `~/.cache/huggingface`。

2. **其它平台（Intel / Windows / Linux）回退 faster-whisper**：
   ```bash
   pip install faster-whisper   # 自动用 large-v3-turbo，CPU 可跑
   ```

## 速度参考

M5 + mlx-whisper large-v3-turbo：30 秒小窗约 1–2 秒/窗，一小时视频约 4–8 分钟。

## 长时任务

全片转写跑后台并留日志，完成后再做对齐校验；不要边看边改 srt。
