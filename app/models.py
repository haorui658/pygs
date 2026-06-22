"""
数据模型：GameConfig 与 AppSettings 数据类。

GameConfig 存储原始路径（可含 <USERPROFILE> / <HOME> 变量），
运行时通过 PathResolver 解析为绝对路径。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.path_resolver import PathResolver


# Windows 目录名非法字符
_ILLEGAL_DIR_CHARS = re.compile(r'[<>:"/\\|?*]')


def _sanitize_dirname(name: str) -> str:
    """将游戏名称转换为合法的目录名。"""
    sanitized = _ILLEGAL_DIR_CHARS.sub("_", name).strip()
    return sanitized if sanitized else "unnamed"


# ---------------------------------------------------------------------------
# GameConfig
# ---------------------------------------------------------------------------

@dataclass
class GameConfig:
    """单条游戏配置。"""

    name: str
    interval: int = 0                      # 秒，0 = 关闭定时备份
    source_path: str = ""                  # 原始形式，可含 <USERPROFILE> / <HOME>
    backup_path: str = ""                  # 原始形式，可含 <USERPROFILE> / <HOME>
    last_fingerprint: Optional[str] = None  # SHA-256 目录指纹
    last_backup_time: str = ""             # 上次备份时间 YYYY-MM-DD HH:MM:SS

    # ------------------------------------------------------------------
    # 路径解析（需要 PathResolver）
    # ------------------------------------------------------------------

    def resolved_source_path(self, resolver: PathResolver) -> str:
        """返回源路径的绝对形式。"""
        return resolver.resolve(self.source_path)

    def resolved_backup_path(self, resolver: PathResolver) -> str:
        """返回备份根路径的绝对形式。"""
        return resolver.resolve(self.backup_path)

    def backup_target_dir(self, resolver: PathResolver) -> str:
        """
        实际备份目标目录：backup_path/{sanitized_name}/
        这样多个游戏可以共用同一个 backup_path 父目录而不会冲突。
        """
        return os.path.join(
            self.resolved_backup_path(resolver),
            _sanitize_dirname(self.name),
        )

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def source_exists(self, resolver: PathResolver) -> bool:
        return os.path.isdir(self.resolved_source_path(resolver))

    def backup_exists(self, resolver: PathResolver) -> bool:
        return os.path.isdir(self.backup_target_dir(resolver))

    def has_interval(self) -> bool:
        return self.interval > 0

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "interval": self.interval,
            "source_path": self.source_path,
            "backup_path": self.backup_path,
            "last_fingerprint": self.last_fingerprint,
            "last_backup_time": self.last_backup_time,
        }

    @staticmethod
    def from_dict(d: dict) -> GameConfig:
        return GameConfig(
            name=d.get("name", ""),
            interval=d.get("interval", 0),
            source_path=d.get("source_path", ""),
            backup_path=d.get("backup_path", ""),
            last_fingerprint=d.get("last_fingerprint"),
            last_backup_time=d.get("last_backup_time", ""),
        )


# ---------------------------------------------------------------------------
# AppSettings
# ---------------------------------------------------------------------------

@dataclass
class AppSettings:
    """应用级设置（独立于游戏配置）。"""

    home_path: str = ""   # <HOME> 映射的绝对路径

    def to_dict(self) -> dict:
        return {
            "home_path": self.home_path,
            "_version": 1,
        }

    @staticmethod
    def from_dict(d: dict) -> AppSettings:
        return AppSettings(
            home_path=d.get("home_path", ""),
        )
