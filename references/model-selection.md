# 模型自动选型 · 机型 → 引擎 → 模型

开工前先跑 `python3 scripts/detect_env.py`，按返回的 `recommended` 选择识别引擎与模型。不要凭经验猜——不同电脑差异巨大。

## 决策表

| 机型 | 引擎 | 模型 | 说话人分离 | 说明 |
|---|---|---|---|---|
| Apple Silicon，≥24GB | mlx-whisper | large-v3 | ✅ | 满血配置，Metal 加速 + 统一内存 |
| Apple Silicon，16GB | mlx-whisper | medium | ✅ | 精度/速度平衡 |
| Apple Silicon，8GB | mlx-whisper | small | ❌ | 保流畅 |
| NVIDIA CUDA，≥10GB 显存 | faster-whisper | large-v3 | ✅ | CTranslate2 加速 |
| NVIDIA CUDA，4–10GB | faster-whisper | medium | ❌ | 稳妥 |
| NVIDIA CUDA，<4GB | faster-whisper | small | ❌ | 兜底 |
| 纯 CPU，≥16GB 内存 | faster-whisper | small (int8) | ❌ | 长视频分段跑 |
| 纯 CPU，<16GB | faster-whisper | base (int8) | ❌ | 保底可用 |

## 安装命令速查

```bash
# Apple Silicon
pip install mlx-whisper

# CUDA / CPU
pip install faster-whisper

# 模型国内镜像加速（任何引擎都建议设）
export HF_ENDPOINT=https://hf-mirror.com
```

## 注意

- **说话人分离**（V1.5 路线）额外需要约 2GB 模型空间；`diarization=false` 的机器不要强行开
- 探测结果只在开工时跑一次，写入工作记录即可，不要每个视频重复探测
- 用户明确指定模型时，以用户为准，探测结果仅作建议
