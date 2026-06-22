"""
SettingsDialog：配置 <HOME> 变量的模态对话框。

<HOME> 是用户自定义路径，可在游戏配置的源/备份路径中作为 <HOME> 占位符使用。
<USERPROFILE> 为只读系统环境变量，仅作显示参考。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog
from typing import TYPE_CHECKING

from app.ui.theme import COLORS, FONT_FAMILY
from app.ui.widgets import make_button, make_browse_row, make_form_label

if TYPE_CHECKING:
    from app.path_resolver import PathResolver
    from app.settings_store import SettingsStore


class SettingsDialog(tk.Toplevel):
    """<HOME> 设置模态对话框。"""

    def __init__(
        self,
        parent: tk.Toplevel | tk.Tk,
        settings_store: SettingsStore,
        path_resolver: PathResolver,
    ) -> None:
        super().__init__(parent)
        self._store = settings_store
        self._resolver = path_resolver

        self.title("设置")
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
        tk.Label(title_bar, text="⚙  设置", font=(FONT_FAMILY, 12, "bold"),
                 fg="white", bg=COLORS["primary"]).pack(side="left", padx=20, pady=8)

        form = tk.Frame(card, bg=COLORS["card"])
        form.pack(fill="both", expand=True, padx=24, pady=(20, 10))

        # <HOME> 设置
        make_form_label(form, "<HOME> 目录", COLORS["card"]).pack(fill="x", **pad)
        home_row, self._entry_home, self._btn_home_browse = make_browse_row(form, "", COLORS["card"])
        home_row.pack(fill="x", padx=20, pady=(4, 0))
        self._btn_home_browse.configure(command=self._browse_home)
        self._entry_home.insert(0, self._resolver.get_home())
        tk.Label(form, text="✦ 此路径将替代游戏配置路径中的 <HOME> 占位符",
                 font=(FONT_FAMILY, 8), fg=COLORS["text_muted"], bg=COLORS["card"],
                 anchor="w").pack(fill="x", padx=24, pady=(2, 0))

        # <USERPROFILE> 只读显示
        make_form_label(form, "当前 <USERPROFILE>（系统环境变量，只读）", COLORS["card"]).pack(fill="x", **pad)
        try:
            up_text = self._resolver.userprofile
        except OSError:
            up_text = "（未设置）"
        tk.Label(form, text=up_text, font=(FONT_FAMILY, 9),
                 fg=COLORS["text_secondary"], bg=COLORS["card"],
                 anchor="w").pack(fill="x", padx=20, pady=(4, 0))

        # 按钮
        btn_row = tk.Frame(card, bg=COLORS["card"])
        btn_row.pack(fill="x", padx=24, pady=(20, 20))

        tk.Button(btn_row, text="取消", command=self.destroy,
                  font=(FONT_FAMILY, 10), bg="#e2e8f0", fg=COLORS["text"],
                  activebackground="#cbd5e1", relief="flat", cursor="hand2",
                  padx=20, pady=4).pack(side="right", padx=(10, 0))
        make_button(btn_row, "保存", COLORS["primary"], COLORS["primary_hover"],
                    self._on_save, bold=True).pack(side="right")

    # ------------------------------------------------------------------
    # 浏览
    # ------------------------------------------------------------------

    def _browse_home(self) -> None:
        path = filedialog.askdirectory(title="选择 <HOME> 目录")
        if path:
            self._entry_home.delete(0, "end")
            self._entry_home.insert(0, path)

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        import os
        from app.models import AppSettings

        path = self._entry_home.get().strip()
        if path:
            path = os.path.normpath(path)
        self._resolver.set_home(path)
        self._store.save(AppSettings(home_path=path))
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
