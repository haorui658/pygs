"""
ConfigDialog：新增 / 修改游戏配置的模态对话框。

- 使用 GameConfig 数据类而非裸字典
- 显示路径变量的原始形式（编辑）和解析后形式（预览）
- 浏览目录后自动通过 PathResolver.compact() 压缩路径
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import TYPE_CHECKING

from app.models import GameConfig
from app.ui.theme import COLORS, FONT_FAMILY
from app.ui.widgets import make_button, make_browse_row, make_form_label, make_resolved_label

if TYPE_CHECKING:
    from app.path_resolver import PathResolver


class ConfigDialog(tk.Toplevel):
    """新增 / 修改游戏配置的模态对话框。"""

    def __init__(
        self,
        parent: tk.Toplevel | tk.Tk,
        path_resolver: PathResolver,
        title: str = "游戏配置",
        config: GameConfig | None = None,
        existing_names: set[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.result: GameConfig | None = None
        self._resolver = path_resolver
        self._config = config
        # 已有的游戏名称集合（不含当前正在编辑的），用于唯一性校验
        self._existing_names: set[str] = existing_names or set()

        self.title(title)
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])

        self._build_ui()
        self._center_on_parent(parent)
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        cfg = self._config
        pad = {"padx": 20, "pady": (12, 0)}

        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=4, pady=4)

        card = tk.Frame(main, bg=COLORS["card"], highlightthickness=1,
                        highlightbackground=COLORS["border"])
        card.pack(fill="both", expand=True)

        # 标题栏
        title_bar = tk.Frame(card, bg=COLORS["primary"], height=40)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text=self.title(), font=(FONT_FAMILY, 12, "bold"),
                 fg="white", bg=COLORS["primary"]).pack(side="left", padx=20, pady=8)

        form = tk.Frame(card, bg=COLORS["card"])
        form.pack(fill="both", expand=True, padx=24, pady=(20, 10))

        # -- 游戏名称 --
        make_form_label(form, "游戏名称", COLORS["card"]).pack(fill="x", **pad)
        self._entry_name = tk.Entry(form, font=(FONT_FAMILY, 10), relief="solid",
                                     borderwidth=1, highlightthickness=0)
        self._entry_name.pack(fill="x", padx=20, pady=(4, 0), ipady=6)
        if cfg:
            self._entry_name.insert(0, cfg.name)

        # -- 定时间隔 --
        make_form_label(form, "定时保存间隔（秒，0 = 关闭）", COLORS["card"]).pack(fill="x", **pad)
        self._spin_interval = tk.Spinbox(form, from_=0, to=86400, increment=10,
                                          font=(FONT_FAMILY, 10), relief="solid",
                                          borderwidth=1, highlightthickness=0)
        self._spin_interval.pack(fill="x", padx=20, pady=(4, 0), ipady=6)
        default_interval = str(cfg.interval) if cfg else "0"
        self._spin_interval.delete(0, "end")
        self._spin_interval.insert(0, default_interval)

        # -- 源路径 --
        make_form_label(form, "源路径（游戏存档目录）", COLORS["card"]).pack(fill="x", **pad)
        src_row, self._entry_src, self._btn_src_browse = make_browse_row(form, "", COLORS["card"])
        src_row.pack(fill="x", padx=20, pady=(4, 0))
        self._btn_src_browse.configure(command=self._browse_src)
        if cfg:
            self._entry_src.insert(0, cfg.source_path)
        # 路径解析预览
        self._lbl_src_resolved = make_resolved_label(form, self._resolve_preview(cfg.source_path if cfg else ""), COLORS["card"])
        self._lbl_src_resolved.pack(fill="x", padx=24, pady=(2, 0))
        self._entry_src.bind("<KeyRelease>", lambda e: self._update_src_preview())

        # -- 备份路径 --
        make_form_label(form, "备份路径（备份存放根目录）", COLORS["card"]).pack(fill="x", **pad)
        dst_row, self._entry_dst, self._btn_dst_browse = make_browse_row(form, "", COLORS["card"])
        dst_row.pack(fill="x", padx=20, pady=(4, 0))
        self._btn_dst_browse.configure(command=self._browse_dst)
        if cfg:
            self._entry_dst.insert(0, cfg.backup_path)
        # 路径解析预览（含子目录提示）
        initial_dst = cfg.backup_path if cfg else ""
        initial_name = cfg.name if cfg else self._entry_name.get()
        self._lbl_dst_resolved = make_resolved_label(
            form,
            self._resolve_preview(initial_dst, show_subdir=True, game_name=initial_name),
            COLORS["card"],
        )
        self._lbl_dst_resolved.pack(fill="x", padx=24, pady=(2, 0))
        self._entry_dst.bind("<KeyRelease>", lambda e: self._update_dst_preview())
        self._entry_name.bind("<KeyRelease>", lambda e: self._update_dst_preview())

        # 提示
        tip = tk.Label(form, text="✦ 路径中可使用 <USERPROFILE> 和 <HOME> 变量，便于跨电脑使用",
                       font=(FONT_FAMILY, 8), fg=COLORS["text_muted"], bg=COLORS["card"], anchor="w")
        tip.pack(fill="x", padx=24, pady=(12, 0))

        # -- 按钮 --
        btn_row = tk.Frame(card, bg=COLORS["card"])
        btn_row.pack(fill="x", padx=24, pady=(20, 20))

        tk.Button(btn_row, text="取消", command=self.destroy,
                  font=(FONT_FAMILY, 10), bg="#e2e8f0", fg=COLORS["text"],
                  activebackground="#cbd5e1", relief="flat", cursor="hand2",
                  padx=20, pady=4).pack(side="right", padx=(10, 0))
        make_button(btn_row, "保存", COLORS["primary"], COLORS["primary_hover"],
                    self._on_save, bold=True).pack(side="right")

    # ------------------------------------------------------------------
    # 路径预览更新
    # ------------------------------------------------------------------

    def _resolve_preview(self, path: str, show_subdir: bool = False, game_name: str = "") -> str:
        if not path:
            return "→ （路径为空）"
        try:
            resolved = self._resolver.resolve(path)
        except Exception:
            resolved = path
        if show_subdir and game_name.strip():
            import re
            safe = re.sub(r'[<>:"/\\|?*]', '_', game_name.strip())
            return f"→ 实际备份到: {os.path.join(resolved, safe)}"
        return f"→ 解析为: {resolved}"

    def _update_src_preview(self) -> None:
        raw = self._entry_src.get()
        self._lbl_src_resolved.configure(text=self._resolve_preview(raw))

    def _update_dst_preview(self) -> None:
        raw = self._entry_dst.get()
        name = self._entry_name.get()
        self._lbl_dst_resolved.configure(text=self._resolve_preview(raw, show_subdir=True, game_name=name))

    # ------------------------------------------------------------------
    # 浏览
    # ------------------------------------------------------------------

    def _browse_src(self) -> None:
        path = filedialog.askdirectory(title="选择游戏存档源目录")
        if path:
            compacted = self._resolver.compact(path)
            self._entry_src.delete(0, "end")
            self._entry_src.insert(0, compacted)
            self._update_src_preview()

    def _browse_dst(self) -> None:
        path = filedialog.askdirectory(title="选择备份根目录")
        if path:
            compacted = self._resolver.compact(path)
            self._entry_dst.delete(0, "end")
            self._entry_dst.insert(0, compacted)
            self._update_dst_preview()

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        name = self._entry_name.get().strip()
        if not name:
            messagebox.showwarning("输入错误", "请输入游戏名称", parent=self)
            return

        # 游戏名称唯一性校验
        if name in self._existing_names:
            messagebox.showwarning(
                "输入错误",
                f"游戏名称「{name}」已存在，请使用其他名称。",
                parent=self,
            )
            return

        try:
            interval = int(self._spin_interval.get())
        except ValueError:
            interval = 0

        src_raw = self._entry_src.get().strip()
        dst_raw = self._entry_dst.get().strip()

        if not src_raw:
            messagebox.showwarning("输入错误", "请选择源路径", parent=self)
            return
        if not dst_raw:
            messagebox.showwarning("输入错误", "请选择备份路径", parent=self)
            return

        # 解析后比较
        src_resolved = self._resolver.resolve(src_raw)
        dst_resolved = self._resolver.resolve(dst_raw)
        if os.path.normpath(src_resolved) == os.path.normpath(dst_resolved):
            messagebox.showwarning("输入错误", "源路径和备份路径不能相同", parent=self)
            return

        # 检查是否有未解析的变量
        unresolvable = self._resolver.validate(src_raw) + self._resolver.validate(dst_raw)
        if unresolvable:
            messagebox.showwarning(
                "输入错误",
                f"路径中包含无法解析的变量: {', '.join(unresolvable)}\n请先在设置中配置 <HOME> 路径。",
                parent=self,
            )
            return

        # 保留旧指纹（仅在源路径未变时）
        old_src = self._config.source_path if self._config else ""
        fingerprint = None
        backup_time = ""
        if self._config and os.path.normpath(self._resolver.resolve(old_src)) == os.path.normpath(src_resolved):
            fingerprint = self._config.last_fingerprint
            backup_time = self._config.last_backup_time

        self.result = GameConfig(
            name=name,
            interval=max(0, interval),
            source_path=src_raw,
            backup_path=dst_raw,
            last_fingerprint=fingerprint,
            last_backup_time=backup_time,
        )
        self.destroy()

    # ------------------------------------------------------------------
    # 定位
    # ------------------------------------------------------------------

    def _center_on_parent(self, parent: tk.Toplevel | tk.Tk) -> None:
        self.update_idletasks()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"+{x}+{y}")
