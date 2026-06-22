"""
可复用的 UI 组件工厂。

所有组件都是纯 tkinter，可从 app/ui/theme.py 获取样式常量。
"""

from __future__ import annotations

import tkinter as tk

from app.ui.theme import COLORS, FONT_FAMILY


def make_button(
    parent: tk.Widget,
    text: str,
    bg: str = COLORS["primary"],
    hover_bg: str = COLORS["primary_hover"],
    command=None,
    bold: bool = False,
) -> tk.Button:
    """创建统一样式的圆角扁平按钮（含 hover 效果）。"""
    weight = "bold" if bold else "normal"
    btn = tk.Button(
        parent,
        text=text,
        font=(FONT_FAMILY, 9, weight),
        bg=bg,
        fg="white",
        activebackground=hover_bg,
        relief="flat",
        cursor="hand2",
        padx=12,
        pady=4,
        command=command,
        bd=0,
    )
    btn.bind("<Enter>", lambda e: e.widget.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda e: e.widget.configure(bg=bg))
    return btn


def make_browse_row(parent: tk.Widget, label: str, bg: str) -> tuple[tk.Frame, tk.Entry, tk.Button]:
    """
    创建一个标签 + 输入框 + 浏览按钮的水平行。
    返回 (row_frame, entry, button)。
    """
    row = tk.Frame(parent, bg=bg)
    entry = tk.Entry(row, font=(FONT_FAMILY, 10), relief="solid",
                     borderwidth=1, highlightthickness=0)
    entry.pack(side="left", fill="x", expand=True, ipady=6)
    btn = tk.Button(row, text="浏览...", font=(FONT_FAMILY, 9),
                    bg=COLORS["primary"], fg="white",
                    activebackground=COLORS["primary_hover"],
                    relief="flat", cursor="hand2", padx=8)
    btn.pack(side="left", padx=(8, 0))
    return row, entry, btn


def make_form_label(parent: tk.Widget, text: str, bg: str) -> tk.Label:
    """创建表单标签。"""
    return tk.Label(parent, text=text, font=(FONT_FAMILY, 10),
                    fg=COLORS["text"], bg=bg, anchor="w")


def make_resolved_label(parent: tk.Widget, text: str, bg: str) -> tk.Label:
    """创建灰色小字路径预览标签。"""
    return tk.Label(parent, text=text, font=(FONT_FAMILY, 8),
                    fg=COLORS["text_muted"], bg=bg, anchor="w")
