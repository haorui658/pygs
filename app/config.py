"""
应用级常量与配置。

仅定义路径、变量名和版本等常量 —— 不包含主题色彩（见 app/ui/theme.py）。
"""

import os
import sys

# ---- 基础路径 ----
# 编译为 exe（Nuitka / PyInstaller）时，使用 exe 所在目录，
# 否则使用源码目录，确保配置文件持久化到正确位置。
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "game_configs.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "app_settings.json")
HISTORY_DIR = os.path.join(BASE_DIR, "history")

# ---- 路径变量占位符 ----
VARIABLE_USERPROFILE = "<USERPROFILE>"
VARIABLE_HOME = "<HOME>"

VALID_VARIABLES = {VARIABLE_USERPROFILE, VARIABLE_HOME}

# ---- 版本 ----
SETTINGS_VERSION = 1
