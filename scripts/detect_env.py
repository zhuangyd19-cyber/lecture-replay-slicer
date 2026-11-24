#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境探测与模型自动选型 · 录像切片师（lecture-replay-slicer）

运行后输出 JSON：
{
  "os": "macos|windows|linux",
  "arch": "arm64|x86_64",
  "chip": "Apple M5" 或 CPU 型号,
  "ram_gb": 32,
  "gpu": {"type": "apple_silicon|cuda|none", "vram_gb": 估算值},
  "recommended": {
    "asr_engine": "mlx-whisper|faster-whisper|funasr",
    "asr_model": "large-v3|...",
    "diarization": true/false,
    "reason": "..."
  }
}

用法：python3 detect_env.py          # 打印 JSON
     python3 detect_env.py --quiet  # 只打印推荐的引擎和模型名
"""
import json
import platform
import subprocess
import sys


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ''


def detect_os():
    s = platform.system()
    return {'Darwin': 'macos', 'Windows': 'windows', 'Linux': 'linux'}.get(s, s.lower())


def detect_ram_gb(os_name):
    try:
        if os_name == 'macos':
            return round(int(_run(['sysctl', '-n', 'hw.memsize'])) / 1073741824)
        if os_name == 'linux':
            for line in open('/proc/meminfo'):
                if line.startswith('MemTotal'):
                    return round(int(line.split()[1]) / 1048576)
        if os_name == 'windows':
            out = _run(['wmic', 'computersystem', 'get', 'totalphysicalmemory'])
            return round(int(out.split()[-1]) / 1073741824)
    except Exception:
        pass
    return 0


def detect_chip(os_name):
    if os_name == 'macos':
        return _run(['sysctl', '-n', 'machdep.cpu.brand_string'])
    return platform.processor() or _run(['wmic', 'cpu', 'get', 'name']) if os_name == 'windows' else platform.processor()


def detect_gpu(os_name):
    """返回 (gpu_type, vram_gb)。Apple Silicon 统一内存按 60% 估算可用显存。"""
    if os_name == 'macos':
        if platform.machine() == 'arm64':
            return 'apple_silicon', None  # 统一内存，后按 RAM 折算
        return 'none', 0
    out = _run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'])
    if out:
        try:
            return 'cuda', round(int(out.split()[0]) / 1024)
        except Exception:
            return 'cuda', None
    return 'none', 0


def recommend(os_name, ram_gb, gpu_type, vram_gb):
    """机型 → (asr_engine, asr_model, diarization, reason)"""
    # Apple Silicon：mlx-whisper 是最优解（Metal 加速 + 统一内存）
    if gpu_type == 'apple_silicon':
        eff_vram = int(ram_gb * 0.6)
        if ram_gb >= 24:
            return ('mlx-whisper', 'large-v3', True,
                    f'Apple Silicon + {ram_gb}GB 统一内存（约 {eff_vram}GB 可用于推理），跑 Whisper large-v3 满血 + 说话人分离')
        if ram_gb >= 16:
            return ('mlx-whisper', 'medium', True,
                    f'Apple Silicon + {ram_gb}GB，medium 精度/速度平衡，可跑说话人分离')
        return ('mlx-whisper', 'small', False,
                f'Apple Silicon + {ram_gb}GB，small 保流畅')
    # NVIDIA CUDA
    if gpu_type == 'cuda':
        v = vram_gb or 0
        if v >= 10:
            return 'faster-whisper', 'large-v3', True,
            f'CUDA 显卡 {v}GB 显存，large-v3 + CTranslate2 加速 + 说话人分离'
        if v >= 4:
            return ('faster-whisper', 'medium', False,
                    f'CUDA 显卡 {v}GB 显存，medium 稳妥')
        return ('faster-whisper', 'small', False, f'CUDA 显存偏小（{v}GB），small 兜底')
    # 纯 CPU
    if ram_gb >= 16:
        return ('faster-whisper', 'small', False,
                f'纯 CPU + {ram_gb}GB 内存，int8 small；长视频建议分段跑')
    return ('faster-whisper', 'base', False,
            f'纯 CPU + {ram_gb}GB 内存，base int8 保底可用')


def main():
    os_name = detect_os()
    arch = platform.machine()
    chip = detect_chip(os_name)
    ram_gb = detect_ram_gb(os_name)
    gpu_type, vram_gb = detect_gpu(os_name)
    engine, model, diar, reason = recommend(os_name, ram_gb, gpu_type, vram_gb)
    result = {
        'os': os_name,
        'arch': arch,
        'chip': chip,
        'ram_gb': ram_gb,
        'gpu': {'type': gpu_type, 'vram_gb': vram_gb},
        'recommended': {
            'asr_engine': engine,
            'asr_model': model,
            'diarization': diar,
            'reason': reason,
        },
    }
    if '--quiet' in sys.argv:
        print(f'{engine} {model} diarization={diar}')
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
