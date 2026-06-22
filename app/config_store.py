"""
ConfigStore：游戏配置列表的 JSON 持久化。

提供原子写入以防止崩溃时损坏配置文件。
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import GameConfig


class ConfigStore:
    """管理 game_configs.json 的读写。"""

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    # ------------------------------------------------------------------
    # 读
    # ------------------------------------------------------------------

    def load(self) -> list[GameConfig]:
        """
        从 JSON 文件加载配置列表。
        文件不存在或损坏时返回空列表。
        """
        # 延迟导入避免循环依赖
        from app.models import GameConfig

        if not os.path.isfile(self._file_path):
            return []

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                raw_list = json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

        if not isinstance(raw_list, list):
            return []

        return [GameConfig.from_dict(d) for d in raw_list if isinstance(d, dict)]

    # ------------------------------------------------------------------
    # 写
    # ------------------------------------------------------------------

    def save(self, configs: list[GameConfig]) -> None:
        """直接写入配置文件。"""
        self._write(self._file_path, configs)

    def atomic_save(self, configs: list[GameConfig]) -> None:
        """
        原子写入：先写临时文件，再 rename 到目标路径。
        防止写入中途崩溃导致配置文件损坏。
        """
        fd, tmp_path = tempfile.mkstemp(
            suffix=".json",
            prefix="game_configs_",
            dir=os.path.dirname(self._file_path) or ".",
        )
        try:
            os.close(fd)
            self._write(tmp_path, configs)
            os.replace(tmp_path, self._file_path)
        except Exception:
            # 清理临时文件
            if os.path.isfile(tmp_path):
                os.unlink(tmp_path)
            raise

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _write(self, path: str, configs: list[GameConfig]) -> None:
        data = [c.to_dict() for c in configs]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
