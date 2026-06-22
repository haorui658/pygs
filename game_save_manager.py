#!/usr/bin/env python3
"""
游戏存档管理器 — 入口点。

将所有服务与 UI 连接在一起并启动 tkinter 主循环。
"""

import tkinter as tk

from app.ui.main_window import MainWindow


def main() -> None:
    root = tk.Tk()
    # 尝试设置窗口图标（可选，忽略错误）
    try:
        root.iconbitmap(default="")
    except tk.TclError:
        pass
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
