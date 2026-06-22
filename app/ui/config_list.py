"""
ConfigListFrame：可滚动的复选框配置列表。

独立 tkinter Frame，通过回调向外通知选择变化。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, TYPE_CHECKING

from app.fingerprint import format_interval, truncate_path
from app.ui.theme import COLORS, FONT_FAMILY

if TYPE_CHECKING:
    from app.models import GameConfig
    from app.path_resolver import PathResolver


class ConfigListFrame(tk.Frame):
    """可滚动的游戏配置列表，每行带复选框。"""

    def __init__(
        self,
        parent: tk.Widget,
        path_resolver: PathResolver,
        on_selection_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=COLORS["card"])
        self._resolver = path_resolver
        self._on_selection_changed = on_selection_changed

        self._configs: list[GameConfig] = []
        self._check_vars: dict[int, tk.BooleanVar] = {}
        self._select_all_var = tk.BooleanVar(value=False)
        self._row_frames: dict[int, tk.Frame] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def set_configs(self, configs: list[GameConfig]) -> None:
        """替换全部配置并重建列表。"""
        self._configs = configs
        self._rebuild()

    def get_selected_indices(self) -> list[int]:
        """返回所有选中行的索引。"""
        return [i for i, v in self._check_vars.items() if v.get()]

    def get_selected_configs(self) -> list[GameConfig]:
        """返回所有选中行的 GameConfig 对象。"""
        return [self._configs[i] for i in self.get_selected_indices() if i < len(self._configs)]

    def select_all(self) -> None:
        for var in self._check_vars.values():
            var.set(True)
        self._select_all_var.set(True)
        self._notify()

    def deselect_all(self) -> None:
        for var in self._check_vars.values():
            var.set(False)
        self._select_all_var.set(False)
        self._notify()

    @property
    def selected_count(self) -> int:
        return sum(1 for v in self._check_vars.values() if v.get())

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # 标题行
        header = tk.Frame(self, bg=COLORS["card"], height=36)
        header.pack(fill="x", padx=16, pady=(10, 0))
        header.pack_propagate(False)

        self._cb_select_all = tk.Checkbutton(
            header, text="全选", variable=self._select_all_var,
            command=self._on_select_all, font=(FONT_FAMILY, 10, "bold"),
            fg=COLORS["text"], bg=COLORS["card"],
            activebackground=COLORS["card"], selectcolor=COLORS["card"])
        self._cb_select_all.pack(side="left")

        # 列标签
        cols = [
            ("游戏名称", 18, "w"),
            ("保存间隔", 14, "center"),
            ("源路径", 36, "w"),
            ("备份路径", 36, "w"),
        ]
        labels_frame = tk.Frame(header, bg=COLORS["card"])
        labels_frame.pack(side="left", fill="x", expand=True, padx=(12, 0))
        for text, width, anchor in cols:
            tk.Label(labels_frame, text=text, font=(FONT_FAMILY, 9, "bold"),
                     fg=COLORS["text_secondary"], bg=COLORS["card"],
                     width=width, anchor=anchor).pack(side="left", padx=4)

        # 分隔线
        tk.Frame(self, bg=COLORS["border"], height=1).pack(fill="x", padx=14, pady=(6, 0))

        # 可滚动区域
        self._canvas = tk.Canvas(self, bg=COLORS["card"], highlightthickness=0, bd=0)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._inner = tk.Frame(self._canvas, bg=COLORS["card"])

        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._window_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=(4, 4))
        self._scrollbar.pack(side="right", fill="y", pady=(4, 4), padx=(0, 6))

        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

    # ------------------------------------------------------------------
    # 列表重建
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        for w in self._inner.winfo_children():
            w.destroy()
        self._check_vars.clear()
        self._row_frames.clear()

        if not self._configs:
            tk.Label(self._inner, text="暂无游戏配置\n点击下方「新增」按钮添加",
                     font=(FONT_FAMILY, 11), fg=COLORS["text_muted"],
                     bg=COLORS["card"]).pack(pady=40)
        else:
            for i, cfg in enumerate(self._configs):
                self._create_row(i, cfg)

        self._select_all_var.set(False)
        self._notify()

    def _create_row(self, index: int, cfg: GameConfig) -> None:
        bg_color = COLORS["card"] if index % 2 == 0 else COLORS["row_odd"]
        alt_bg = COLORS["card"] if index % 2 == 0 else COLORS["row_odd"]

        row = tk.Frame(self._inner, bg=bg_color, height=40)
        row.pack(fill="x", padx=4, pady=1)
        row.pack_propagate(False)
        self._row_frames[index] = row

        # hover
        row.bind("<Enter>", lambda e, r=row: r.configure(bg=COLORS["row_hover"]))
        row.bind("<Leave>", lambda e, r=row, a=alt_bg: r.configure(bg=a))
        row.bind("<Double-Button-1>", lambda e, i=index: self._on_double_click(i))

        # 复选框
        var = tk.BooleanVar(value=False)
        self._check_vars[index] = var
        cb = tk.Checkbutton(row, variable=var, command=self._notify,
                            bg=bg_color, activebackground=COLORS["row_hover"],
                            selectcolor=COLORS["card"])
        cb.pack(side="left", padx=(8, 4))
        cb.bind("<Enter>", lambda e, r=row, c=cb:
                (r.configure(bg=COLORS["row_hover"]),
                 c.configure(bg=COLORS["row_hover"], activebackground=COLORS["row_hover"])))
        cb.bind("<Leave>", lambda e, r=row, c=cb, a=alt_bg:
                (r.configure(bg=a),
                 c.configure(bg=a, activebackground=a)))

        # 游戏名称
        self._add_cell(row, cfg.name, 10, True, COLORS["text"], 18, "w", alt_bg)

        # 间隔
        interval_text = format_interval(cfg.interval)
        int_color = COLORS["primary"] if cfg.interval > 0 else COLORS["text_muted"]
        self._add_cell(row, interval_text, 9, False, int_color, 14, "center", alt_bg)

        # 源路径（显示解析后的路径）
        src_resolved = cfg.resolved_source_path(self._resolver)
        src_display = truncate_path(src_resolved if src_resolved else cfg.source_path)
        self._add_cell(row, src_display, 9, False, COLORS["text_secondary"], 36, "w", alt_bg)

        # 备份路径
        dst_resolved = cfg.resolved_backup_path(self._resolver)
        dst_display = truncate_path(dst_resolved if dst_resolved else cfg.backup_path)
        self._add_cell(row, dst_display, 9, False, COLORS["text_secondary"], 36, "w", alt_bg)

        # 上次备份时间
        last_time = cfg.last_backup_time
        time_display = f"上次: {last_time}" if last_time else "尚未备份"
        time_lbl = tk.Label(row, text=time_display, font=(FONT_FAMILY, 8),
                            fg=COLORS["text_muted"], bg=bg_color, anchor="e")
        time_lbl.pack(side="right", padx=(4, 12))
        time_lbl.bind("<Enter>", lambda e, r=row: r.configure(bg=COLORS["row_hover"]))
        time_lbl.bind("<Leave>", lambda e, r=row, a=alt_bg: r.configure(bg=a))
        time_lbl.bind("<Button-1>", lambda e, i=index: self._toggle_row(i))

    def _add_cell(
        self, row: tk.Frame, text: str, font_size: int, bold: bool,
        fg: str, width: int, anchor: str, alt_bg: str,
    ) -> tk.Label:
        weight = "bold" if bold else "normal"
        lbl = tk.Label(row, text=text, font=(FONT_FAMILY, font_size, weight),
                       fg=fg, bg=row["bg"], anchor=anchor, width=width)
        lbl.pack(side="left", padx=4)
        lbl.bind("<Enter>", lambda e, r=row: r.configure(bg=COLORS["row_hover"]))
        lbl.bind("<Leave>", lambda e, r=row, a=alt_bg: r.configure(bg=a))
        lbl.bind("<Button-1>", lambda e, i=self._row_index(row): self._toggle_row(i))
        return lbl

    def _row_index(self, row: tk.Frame) -> int:
        for i, r in self._row_frames.items():
            if r is row:
                return i
        return -1

    def _toggle_row(self, index: int) -> None:
        if index in self._check_vars:
            self._check_vars[index].set(not self._check_vars[index].get())
            self._notify()

    def _on_double_click(self, index: int) -> None:
        """双击事件由父级处理，这里留空，由 MainWindow 绑定。"""
        pass  # 通过回调外部处理

    # ------------------------------------------------------------------
    # 选择事件
    # ------------------------------------------------------------------

    def _on_select_all(self) -> None:
        state = self._select_all_var.get()
        for var in self._check_vars.values():
            var.set(state)
        self._notify()

    def _notify(self) -> None:
        # 同步全选框
        if self._check_vars:
            all_checked = all(v.get() for v in self._check_vars.values())
            self._select_all_var.set(all_checked)
        if self._on_selection_changed:
            self._on_selection_changed()

    # ------------------------------------------------------------------
    # 滚轮 / 画布
    # ------------------------------------------------------------------

    def _bind_mousewheel(self, event: tk.Event) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event: tk.Event) -> None:
        self._canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event: tk.Event) -> None:
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_configure(self, event: tk.Event) -> None:
        if event.width > 10:
            self._canvas.itemconfig(self._window_id, width=event.width)

    # ------------------------------------------------------------------
    # 双击回调注册（供 MainWindow 使用）
    # ------------------------------------------------------------------

    def bind_double_click(self, callback: Callable[[int], None]) -> None:
        """注册双击行时的回调。"""
        self._on_double_click = callback
