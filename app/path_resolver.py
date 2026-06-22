"""
PathResolver：管理 <USERPROFILE> 和 <HOME> 路径变量的解析与压缩。

- resolve()      — 将变量占位符替换为实际绝对路径
- compact()      — 将绝对路径压缩回含变量的紧凑形式（用于保存）
- validate()     — 检查路径中是否有无法解析的变量
- is_resolvable() — 所有变量均可解析？
"""

from __future__ import annotations

import os


class PathResolver:
    """路径变量解析器。"""

    VAR_USERPROFILE = "<USERPROFILE>"
    VAR_HOME = "<HOME>"

    def __init__(self, home_path: str = "") -> None:
        self._home_path: str = os.path.normpath(home_path) if home_path else ""

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    def set_home(self, path: str) -> None:
        """设置 <HOME> 对应的实际路径。"""
        self._home_path = os.path.normpath(path) if path else ""

    def get_home(self) -> str:
        return self._home_path

    @property
    def userprofile(self) -> str:
        """返回 USERPROFILE 环境变量值。若缺失则抛出 OSError。"""
        val = os.environ.get("USERPROFILE", "")
        if not val:
            raise OSError("USERPROFILE 环境变量未设置")
        return os.path.normpath(val)

    # ------------------------------------------------------------------
    # 核心方法
    # ------------------------------------------------------------------

    def resolve(self, path: str) -> str:
        """
        将路径中的 <USERPROFILE> 和 <HOME> 替换为实际值。
        返回规范化后的绝对路径。
        """
        if not path:
            return path

        result = path

        # 替换 <USERPROFILE>
        try:
            up = self.userprofile
            result = result.replace(self.VAR_USERPROFILE, up)
        except OSError:
            pass  # 保留占位符，调用方自行处理

        # 替换 <HOME>
        if self._home_path and self.VAR_HOME in result:
            result = result.replace(self.VAR_HOME, self._home_path)

        return os.path.normpath(result)

    def compact(self, absolute_path: str) -> str:
        """
        将绝对路径压缩回含变量占位符的形式。
        优先匹配 <HOME>（用户自定义），其次 <USERPROFILE>。
        如果不能压缩，返回原路径。
        """
        if not absolute_path:
            return absolute_path

        norm = os.path.normpath(absolute_path)

        # 尝试 <HOME> 优先
        if self._home_path:
            home_norm = os.path.normpath(self._home_path)
            if norm.startswith(home_norm + os.sep) or norm == home_norm:
                relative = norm[len(home_norm):].lstrip(os.sep).replace("\\", "/")
                return f"{self.VAR_HOME}/{relative}" if relative else self.VAR_HOME

        # 尝试 <USERPROFILE>
        try:
            up = self.userprofile
            if norm.startswith(up + os.sep) or norm == up:
                relative = norm[len(up):].lstrip(os.sep).replace("\\", "/")
                return f"{self.VAR_USERPROFILE}/{relative}" if relative else self.VAR_USERPROFILE
        except OSError:
            pass

        return norm

    def validate(self, path: str) -> list[str]:
        """
        返回路径中无法解析的变量名列表。
        空列表 = 完全可解析。
        """
        unresolved: list[str] = []

        if self.VAR_HOME in path and not self._home_path:
            unresolved.append(self.VAR_HOME)

        if self.VAR_USERPROFILE in path:
            try:
                self.userprofile
            except OSError:
                unresolved.append(self.VAR_USERPROFILE)

        return unresolved

    def is_resolvable(self, path: str) -> bool:
        """路径中所有变量均可解析？"""
        return len(self.validate(path)) == 0
