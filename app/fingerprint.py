"""
实用函数：目录指纹、时间格式化、路径截断。
"""

import os
import json
import hashlib
from datetime import datetime


# ---------------------------------------------------------------------------
# 目录指纹（变更检测）
# ---------------------------------------------------------------------------

def get_dir_fingerprint(path: str) -> str | None:
    """
    计算目录指纹（基于所有文件的 相对路径 + mtime + size）。
    用于检测存档目录是否发生变更。
    跳过以 . 开头的文件和目录。
    返回 SHA-256 十六进制摘要，若路径不存在或不可读则返回 None。
    """
    if not os.path.isdir(path):
        return None

    items: list[tuple[str, float, int]] = []
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f.startswith("."):
                    continue
                fp = os.path.join(root, f)
                try:
                    stat = os.stat(fp)
                    items.append((
                        os.path.relpath(fp, path).replace("\\", "/"),
                        stat.st_mtime,
                        stat.st_size,
                    ))
                except OSError:
                    continue
        items.sort(key=lambda x: x[0])
        raw = json.dumps(items, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# 显示辅助
# ---------------------------------------------------------------------------

def format_interval(seconds: int) -> str:
    """将秒数格式化为人类可读的中文字符串。"""
    if seconds <= 0:
        return "关闭"
    if seconds < 60:
        return f"每 {seconds} 秒"
    if seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"每 {m} 分 {s} 秒" if s else f"每 {m} 分钟"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"每 {h} 时 {m} 分" if m else f"每 {h} 小时"


def truncate_path(path: str, max_len: int = 38) -> str:
    """截断过长的路径用于列表显示。"""
    if len(path) <= max_len:
        return path
    suffix_len = max_len // 3
    prefix_len = max_len - 3 - suffix_len
    if suffix_len > 0:
        return path[:prefix_len] + "..." + path[-suffix_len:]
    return path[:prefix_len] + "..."


def now_str() -> str:
    """返回当前时间字符串 YYYY-MM-DD HH:MM:SS。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def timestamp_str() -> str:
    """返回当前时间戳字符串 YYYYMMDD_HHMMSS（适合文件名）。"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
