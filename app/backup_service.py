"""
BackupService：备份与还原的核心业务逻辑。

- 纯逻辑层，不依赖 tkinter
- 通过 on_status 回调报告进度（供 UI 层消费）
- 备份目标使用 backup_path/{game_name}/ 子目录
- 还原前将当前源目录备份到 history/
"""

from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from app.fingerprint import get_dir_fingerprint, now_str, timestamp_str

if TYPE_CHECKING:
    from app.models import GameConfig
    from app.path_resolver import PathResolver


# ---------------------------------------------------------------------------
# 结果类型
# ---------------------------------------------------------------------------

@dataclass
class OpResult:
    """单次操作结果。"""
    success: bool
    message: str
    config_name: str


# ---------------------------------------------------------------------------
# BackupService
# ---------------------------------------------------------------------------

class BackupService:
    """备份 / 还原业务逻辑。不负责持久化——由调用方在操作完成后保存配置。"""

    def __init__(
        self,
        path_resolver: PathResolver,
        history_dir: str,
    ) -> None:
        self._resolver = path_resolver
        self._history_dir = history_dir
        self._lock = threading.Lock()
        self._is_operating = False

    # ------------------------------------------------------------------
    # 公共属性
    # ------------------------------------------------------------------

    @property
    def is_operating(self) -> bool:
        return self._is_operating

    @property
    def lock(self) -> threading.Lock:
        return self._lock

    # ------------------------------------------------------------------
    # 备份
    # ------------------------------------------------------------------

    def backup(self, config: GameConfig, on_status: Callable[[str], None] | None = None) -> OpResult:
        """备份单个游戏配置。"""
        return self._do_backup(config, on_status)

    def backup_batch(
        self,
        configs: list[GameConfig],
        on_status: Callable[[str], None] | None = None,
    ) -> list[OpResult]:
        """批量备份。"""
        results: list[OpResult] = []
        with self._lock:
            self._is_operating = True
            try:
                for cfg in configs:
                    results.append(self._do_backup(cfg, on_status))
            finally:
                self._is_operating = False
        return results

    def _do_backup(self, config: GameConfig, on_status: Callable[[str], None] | None) -> OpResult:
        name = config.name
        src = config.resolved_source_path(self._resolver)

        if not os.path.isdir(src):
            msg = f"[{name}] 源路径不存在: {src}"
            if on_status:
                on_status(msg)
            return OpResult(False, msg, name)

        # 备份目标: backup_path/{game_name}/
        dst = config.backup_target_dir(self._resolver)

        try:
            os.makedirs(dst, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)

            # 更新指纹
            config.last_fingerprint = get_dir_fingerprint(src)
            config.last_backup_time = now_str()

            msg = f"[{name}] 备份成功 → {dst}"
            if on_status:
                on_status(msg)
            return OpResult(True, msg, name)
        except OSError as e:
            msg = f"[{name}] 备份失败: {e}"
            if on_status:
                on_status(msg)
            return OpResult(False, msg, name)

    # ------------------------------------------------------------------
    # 还原
    # ------------------------------------------------------------------

    def restore(self, config: GameConfig, on_status: Callable[[str], None] | None = None) -> OpResult:
        """还原单个游戏配置。"""
        return self._do_restore(config, on_status)

    def restore_batch(
        self,
        configs: list[GameConfig],
        on_status: Callable[[str], None] | None = None,
    ) -> list[OpResult]:
        """批量还原。"""
        results: list[OpResult] = []
        with self._lock:
            self._is_operating = True
            try:
                for cfg in configs:
                    results.append(self._do_restore(cfg, on_status))
            finally:
                self._is_operating = False
        return results

    def _do_restore(self, config: GameConfig, on_status: Callable[[str], None] | None) -> OpResult:
        name = config.name
        src = config.resolved_source_path(self._resolver)
        backup_src = config.backup_target_dir(self._resolver)  # backup_path/{game_name}/

        if not os.path.isdir(backup_src):
            msg = f"[{name}] 备份目录不存在: {backup_src}"
            if on_status:
                on_status(msg)
            return OpResult(False, msg, name)

        try:
            # 步骤 1：备份当前源目录到 history
            if os.path.isdir(src):
                history_name = f"{name}_{timestamp_str()}"
                history_path = os.path.join(self._history_dir, history_name)
                os.makedirs(self._history_dir, exist_ok=True)
                if on_status:
                    on_status(f"[{name}] 正在备份当前源目录到 history ...")
                shutil.copytree(src, history_path)
                if on_status:
                    on_status(f"[{name}] 已备份到: {history_path}")

            # 步骤 2：删除源目录
            if os.path.isdir(src):
                shutil.rmtree(src)
                if on_status:
                    on_status(f"[{name}] 已删除源目录")

            # 步骤 3：从备份子目录还原
            if on_status:
                on_status(f"[{name}] 正在还原 ...")
            shutil.copytree(backup_src, src)

            # 更新指纹
            config.last_fingerprint = get_dir_fingerprint(src)
            config.last_backup_time = now_str()

            msg = f"[{name}] 还原成功"
            if on_status:
                on_status(msg)
            return OpResult(True, msg, name)
        except OSError as e:
            msg = f"[{name}] 还原失败: {e}"
            if on_status:
                on_status(msg)
            return OpResult(False, msg, name)

    # ------------------------------------------------------------------
    # 指纹（供定时器调用）
    # ------------------------------------------------------------------

    def current_fingerprint(self, config: GameConfig) -> str | None:
        """获取当前源目录的指纹。"""
        return get_dir_fingerprint(config.resolved_source_path(self._resolver))

    def fingerprint_changed(self, config: GameConfig) -> bool:
        """源目录指纹与上次备份时相比是否发生了变化。"""
        current = self.current_fingerprint(config)
        if current is None:
            return False
        stored = config.last_fingerprint
        return stored is None or current != stored
