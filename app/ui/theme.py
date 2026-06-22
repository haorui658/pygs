"""
UI 主题：配色方案、字体、ttk 样式。
"""

import os
from tkinter import ttk

# ---- 配色方案 ----
COLORS = {
    "bg":              "#f0f2f5",
    "card":            "#ffffff",
    "primary":         "#4a6cf7",
    "primary_hover":   "#3b5de7",
    "success":         "#10b981",
    "success_hover":   "#059669",
    "danger":          "#ef4444",
    "danger_hover":    "#dc2626",
    "warning":         "#f59e0b",
    "text":            "#1e293b",
    "text_secondary":  "#64748b",
    "text_muted":      "#94a3b8",
    "border":          "#e2e8f0",
    "row_hover":       "#f8fafc",
    "row_odd":         "#fafbfc",
    "switch_off":      "#cbd5e1",
    "switch_on":       "#4a6cf7",
}

# ---- 字体 ----
FONT_FAMILY = "Microsoft YaHei" if os.name == "nt" else "sans-serif"


def setup_styles() -> None:
    """配置 ttk 全局样式。"""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except ttk.TclError:
        pass

    style.configure("Vertical.TScrollbar",
                    background=COLORS["border"],
                    troughcolor=COLORS["bg"],
                    arrowcolor=COLORS["text_secondary"],
                    bordercolor=COLORS["bg"],
                    lightcolor=COLORS["bg"],
                    darkcolor=COLORS["bg"])
