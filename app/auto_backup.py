"""
AutoBackupTimer：定时自动备份。

在后台线程中运行，遍历所有配置，按各自的间隔检查源目录指纹变化，
检测到变更时自动执行备份。
"""

from __future__ import annotations

import threading
import time
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from app.backup_service import BackupService
    from app.config_store import ConfigStore
    from app.path_resolver import PathResolver


class AutoBackupTimer:
    """定时自动备份调度器。"""

    def __init__(
        self,
        backup_service: BackupService,
        config_store: ConfigStore,
        path_resolver: PathResolver,
        on_status: Callable[[str], None] | None = None,
        on_config_changed: Callable[[], None] | None = None,
    ) -> None:
        self._backup_service = backup_service
        self._config_store = config_store
        self._resolver = path_resolver
        self._on_status = on_status
        self._on_config_changed = on_config_changed

        self._enabled = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_check: dict[str, float] = {}

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._enabled

    def start(self) -> None:
        """启动定时器线程。"""
        if self._enabled:
            return
        self._enabled = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止定时器线程。"""
        if not self._enabled:
            return
        self._enabled = False
        self._stop_event.set()

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """定时器主循环（后台线程）。"""
        while not self._stop_event.is_set():
            # 手动操作进行中则跳过
            if self._backup_service.is_operating:
                self._stop_event.wait(1.0)
                continue

            # 快照当前配置列表
            configs = self._config_store.load()

            for cfg in configs:
                if self._stop_event.is_set():
                    break

                if not cfg.has_interval():
                    continue

                src = cfg.resolved_source_path(self._resolver)
                if not src or not cfg.source_exists(self._resolver):
                    continue

                # 距上次检查是否已过足够时间
                now = time.time()
                last = self._last_check.get(cfg.name, 0)
                if now - last < cfg.interval:
                    continue

                self._last_check[cfg.name] = now

                # 检查指纹变化
                if self._backup_service.fingerprint_changed(cfg):
                    if self._on_status:
                        self._on_status(f"[自动] 检测到 [{cfg.name}] 变更，正在备份 ...")
                    self._backup_service.backup(cfg, self._on_status)
                    # backup() 已更新 cfg 的指纹和时间戳，直接持久化
                    self._config_store.save(configs)
                    # 通知主窗口重新加载配置
                    if self._on_config_changed:
                        self._on_config_changed()

            self._stop_event.wait(2.0)
