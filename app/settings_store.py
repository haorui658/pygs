"""
SettingsStore：应用级设置的 JSON 持久化（app_settings.json）。
"""

from __future__ import annotations

import json
import os

from app.models import AppSettings


class SettingsStore:
    """管理 app_settings.json 的读写。"""

    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    def load(self) -> AppSettings:
        """加载设置。文件不存在或损坏时返回默认值。"""
        if not os.path.isfile(self._file_path):
            return AppSettings()

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, IOError):
            return AppSettings()

        if not isinstance(raw, dict):
            return AppSettings()

        return AppSettings.from_dict(raw)

    def save(self, settings: AppSettings) -> None:
        """保存设置。"""
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)

    def get_home_path(self) -> str:
        """快捷方法：获取 <HOME> 路径。"""
        return self.load().home_path
