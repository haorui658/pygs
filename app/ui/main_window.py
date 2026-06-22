"""
MainWindow：主应用窗口 —— 将 UI 与所有服务层连接在一起。

职责：
- 创建并持有 ConfigStore、SettingsStore、PathResolver、BackupService、AutoBackupTimer
- 构建 tkinter UI（使用 ConfigListFrame 和按钮）
- 响应用户操作，调用服务层方法
- 管理后台线程和定时器
- 本身不包含备份/还原/定时器业务逻辑
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox
import threading

from app.config import CONFIG_FILE, SETTINGS_FILE, HISTORY_DIR
from app.models import GameConfig
from app.path_resolver import PathResolver
from app.config_store import ConfigStore
from app.settings_store import SettingsStore
from app.backup_service import BackupService
from app.auto_backup import AutoBackupTimer
from app.fingerprint import format_interval, truncate_path, now_str

from app.ui.theme import COLORS, FONT_FAMILY, setup_styles
from app.ui.widgets import make_button
from app.ui.config_list import ConfigListFrame
from app.ui.config_dialog import ConfigDialog
from app.ui.settings_dialog import SettingsDialog


class MainWindow:
    """游戏存档管理器主界面。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("游戏存档管理器")
        self.root.geometry("1000x650")
        self.root.minsize(780, 480)
        self.root.configure(bg=COLORS["bg"])

        # ---- 初始化服务层 ----
        setup_styles()

        self._settings_store = SettingsStore(SETTINGS_FILE)
        settings = self._settings_store.load()

        self._resolver = PathResolver(home_path=settings.home_path)
        self._config_store = ConfigStore(CONFIG_FILE)
        self._configs: list[GameConfig] = self._config_store.load()

        self._backup_service = BackupService(self._resolver, HISTORY_DIR)
        self._timer = AutoBackupTimer(
            self._backup_service, self._config_store, self._resolver,
            on_status=self._push_status,
            on_config_changed=self._on_timer_config_changed,
        )

        # 状态
        self._is_operating = False
        self._timer_enabled = False

        # ---- 构建 UI ----
        self._build_ui()

        # ---- 填充列表 ----
        self._list_frame.set_configs(self._configs)

        # ---- 退出处理 ----
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ==================================================================
    # UI 构建
    # ==================================================================

    def _build_ui(self) -> None:
        # ---- 顶部标题栏 ----
        header = tk.Frame(self.root, bg=COLORS["primary"], height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🎮  游戏存档管理器", font=(FONT_FAMILY, 15, "bold"),
                 fg="white", bg=COLORS["primary"]).pack(side="left", padx=24, pady=10)

        # 右侧：设置 + 定时开关
        right_frame = tk.Frame(header, bg=COLORS["primary"])
        right_frame.pack(side="right", padx=20, pady=10)

        # 定时状态
        self._lbl_timer_status = tk.Label(right_frame, text="定时备份: 关闭",
                                          font=(FONT_FAMILY, 9), fg="#cbd5e1",
                                          bg=COLORS["primary"])
        self._lbl_timer_status.pack(side="right", padx=(8, 0))

        self._btn_toggle = tk.Button(right_frame, text="● 开启", width=10,
                                     font=(FONT_FAMILY, 9, "bold"),
                                     bg=COLORS["switch_off"], fg="white",
                                     activebackground=COLORS["switch_on"],
                                     relief="flat", cursor="hand2",
                                     command=self._toggle_timer)
        self._btn_toggle.pack(side="right", padx=(4, 0))

        # 设置按钮
        tk.Button(right_frame, text="⚙ 设置", font=(FONT_FAMILY, 9),
                  bg=COLORS["primary"], fg="white",
                  activebackground=COLORS["primary_hover"],
                  relief="flat", cursor="hand2",
                  command=self._open_settings).pack(side="right", padx=(0, 8))

        # ---- 主体 ----
        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(14, 0))

        # 列表卡片
        list_card = tk.Frame(body, bg=COLORS["card"], highlightthickness=1,
                             highlightbackground=COLORS["border"])
        list_card.pack(fill="both", expand=True)

        self._list_frame = ConfigListFrame(
            list_card, self._resolver,
            on_selection_changed=self._on_selection_changed,
        )
        self._list_frame.pack(fill="both", expand=True)
        self._list_frame.bind_double_click(self._on_double_click_row)

        # ---- 底部操作栏 ----
        bottom_card = tk.Frame(body, bg=COLORS["card"], highlightthickness=1,
                               highlightbackground=COLORS["border"])
        bottom_card.pack(fill="x", pady=(10, 10))

        bottom_inner = tk.Frame(bottom_card, bg=COLORS["card"])
        bottom_inner.pack(fill="x", padx=20, pady=(10, 6))

        # 选中计数
        self._lbl_selected = tk.Label(bottom_inner, text="已选择: 0 项",
                                      font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
                                      bg=COLORS["card"])
        self._lbl_selected.pack(side="left", pady=4)

        # 按钮组
        btn_group = tk.Frame(bottom_inner, bg=COLORS["card"])
        btn_group.pack(side="right")

        make_button(btn_group, "➕  新增", COLORS["primary"], COLORS["primary_hover"],
                    self._add_config).pack(side="left", padx=(0, 6))
        make_button(btn_group, "✏️  修改", COLORS["primary"], COLORS["primary_hover"],
                    self._edit_config).pack(side="left", padx=(0, 6))
        make_button(btn_group, "🗑  删除", COLORS["danger"], COLORS["danger_hover"],
                    self._delete_config).pack(side="left", padx=(0, 16))

        tk.Frame(btn_group, bg=COLORS["border"], width=1).pack(side="left", fill="y", padx=(0, 16))

        make_button(btn_group, "📦  备份选中", COLORS["success"], COLORS["success_hover"],
                    self._backup_selected, bold=True).pack(side="left", padx=(0, 8))
        make_button(btn_group, "🔄  还原选中", COLORS["warning"], "#d97706",
                    self._restore_selected, bold=True).pack(side="left")

        # ---- 状态栏 ----
        status_bar = tk.Frame(self.root, bg=COLORS["card"], height=28,
                              highlightthickness=1, highlightbackground=COLORS["border"])
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)
        self._lbl_status = tk.Label(status_bar, text="就绪",
                                    font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
                                    bg=COLORS["card"], anchor="w")
        self._lbl_status.pack(side="left", padx=16, pady=4)

    # ==================================================================
    # 事件处理
    # ==================================================================

    def _on_selection_changed(self) -> None:
        self._lbl_selected.configure(text=f"已选择: {self._list_frame.selected_count} 项")

    def _on_double_click_row(self, index: int) -> None:
        if 0 <= index < len(self._configs):
            self._edit_config_by_index(index)

    # ==================================================================
    # 增 / 删 / 改
    # ==================================================================

    def _reload_from_disk(self) -> None:
        """从磁盘重新加载配置（静默，不刷新 UI）。"""
        self._configs = self._config_store.load()

    def _find_config_by_name(self, name: str) -> GameConfig | None:
        """根据游戏名称查找配置，找不到返回 None。"""
        for c in self._configs:
            if c.name == name:
                return c
        return None

    def _add_config(self) -> None:
        # 从磁盘加载最新数据，避免覆盖自动备份的更新
        self._reload_from_disk()
        existing_names = {c.name for c in self._configs}

        dlg = ConfigDialog(self.root, self._resolver, "新增游戏配置",
                           existing_names=existing_names)
        if dlg.result:
            # 再次从磁盘加载，防止自动备份在对话框打开期间更新了数据
            self._reload_from_disk()
            if dlg.result.name in {c.name for c in self._configs}:
                messagebox.showwarning("提示", f"游戏「{dlg.result.name}」已存在，无法添加")
                self._list_frame.set_configs(self._configs)
                return
            self._configs.append(dlg.result)
            self._config_store.save(self._configs)
            self._list_frame.set_configs(self._configs)
            self._set_status(f"已添加: {dlg.result.name}")

    def _edit_config(self) -> None:
        selected = self._list_frame.get_selected_indices()
        if not selected:
            messagebox.showinfo("提示", "请先勾选要修改的游戏")
            return
        self._edit_config_by_index(selected[0])

    def _edit_config_by_index(self, index: int) -> None:
        if index < 0 or index >= len(self._configs):
            return

        # 在重载前捕获原名称
        original_name = self._configs[index].name
        self._reload_from_disk()
        cfg = self._find_config_by_name(original_name)
        if cfg is None:
            messagebox.showwarning("提示", f"游戏「{original_name}」已不存在")
            self._list_frame.set_configs(self._configs)
            return

        # 其他游戏名称不可与此冲突
        existing_names = {c.name for c in self._configs if c.name != original_name}

        dlg = ConfigDialog(self.root, self._resolver, "修改游戏配置",
                           config=cfg, existing_names=existing_names)
        if dlg.result:
            # 再次从磁盘加载，防止自动备份在对话框打开期间更新了数据
            self._reload_from_disk()
            target = self._find_config_by_name(original_name)
            if target is None:
                # 理论上不会发生（自动备份不删配置），做防御性处理
                self._configs.append(dlg.result)
            else:
                # 只更新用户可编辑字段，保留磁盘上的最新指纹和时间戳
                # （除非源路径发生变更）
                src_changed = (
                    os.path.normpath(self._resolver.resolve(target.source_path))
                    != os.path.normpath(self._resolver.resolve(dlg.result.source_path))
                )
                target.name = dlg.result.name
                target.interval = dlg.result.interval
                target.source_path = dlg.result.source_path
                target.backup_path = dlg.result.backup_path
                if src_changed:
                    target.last_fingerprint = None
                    target.last_backup_time = ""

            self._config_store.save(self._configs)
            self._list_frame.set_configs(self._configs)
            self._set_status(f"已修改: {dlg.result.name}")

    def _delete_config(self) -> None:
        selected = self._list_frame.get_selected_indices()
        if not selected:
            messagebox.showinfo("提示", "请先勾选要删除的游戏")
            return

        # 在重载前捕获选中游戏名称（重载后索引可能变化）
        names_to_delete = [self._configs[i].name for i in selected if i < len(self._configs)]
        if not names_to_delete:
            return

        msg = f"确定要删除以下 {len(names_to_delete)} 个游戏配置吗？\n\n" + "\n".join(f"  • {n}" for n in names_to_delete)
        msg += "\n\n（仅删除配置，不会删除已备份的存档文件）"

        if messagebox.askyesno("确认删除", msg):
            # 从磁盘加载最新数据，根据名称删除
            self._reload_from_disk()
            self._configs = [c for c in self._configs if c.name not in names_to_delete]
            self._config_store.save(self._configs)
            self._list_frame.set_configs(self._configs)
            self._set_status(f"已删除 {len(names_to_delete)} 个配置")

    # ==================================================================
    # 备份 / 还原
    # ==================================================================

    def _backup_selected(self) -> None:
        configs = self._list_frame.get_selected_configs()
        if not configs:
            messagebox.showinfo("提示", "请先勾选要备份的游戏")
            return

        names = [c.name for c in configs]
        if not messagebox.askyesno("确认备份", f"将备份以下 {len(configs)} 个游戏:\n\n" +
                                    "\n".join(f"  • {n}" for n in names) +
                                    "\n\n源 → 备份路径 / 游戏名\n确认继续？"):
            return

        self._run_in_background(
            lambda: self._backup_service.backup_batch(configs, on_status=self._push_status),
            "备份",
        )

    def _restore_selected(self) -> None:
        configs = self._list_frame.get_selected_configs()
        if not configs:
            messagebox.showinfo("提示", "请先勾选要还原的游戏")
            return

        names = [c.name for c in configs]
        if not messagebox.askyesno("⚠ 确认还原",
                                    f"将还原以下 {len(configs)} 个游戏:\n\n" +
                                    "\n".join(f"  • {n}" for n in names) +
                                    "\n\n还原流程:\n"
                                    "  ① 备份当前源目录 → history/（含时间戳）\n"
                                    "  ② 删除当前源目录\n"
                                    "  ③ 从备份路径/游戏名 完整还原\n\n"
                                    "此操作不可撤销，确认继续？"):
            return

        self._run_in_background(
            lambda: self._backup_service.restore_batch(configs, on_status=self._push_status),
            "还原",
        )

    # ==================================================================
    # 后台操作
    # ==================================================================

    def _run_in_background(self, target, op_name: str) -> None:
        """在后台线程执行操作，防止 UI 卡顿。"""
        if self._is_operating:
            messagebox.showinfo("提示", "正在进行其他操作，请等待完成后再试。")
            return

        self._is_operating = True
        self._set_status(f"{op_name}进行中...")

        def worker() -> None:
            try:
                target()
            except Exception as e:
                self._push_status(f"{op_name}出错: {e}")
            finally:
                self._is_operating = False
                # 在主线程上持久化更新后的指纹和时间戳
                self.root.after(0, self._save_and_reload)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _save_and_reload(self) -> None:
        """在主线程上保存配置并重新加载 UI。"""
        self._config_store.save(self._configs)
        self._configs = self._config_store.load()
        self._list_frame.set_configs(self._configs)

    # ==================================================================
    # 定时器
    # ==================================================================

    def _toggle_timer(self) -> None:
        if self._timer.is_running:
            self._timer.stop()
            self._timer_enabled = False
            self._btn_toggle.configure(text="● 开启", bg=COLORS["switch_off"],
                                       activebackground=COLORS["switch_on"])
            self._lbl_timer_status.configure(text="定时备份: 关闭", fg="#cbd5e1")
            self._set_status("定时备份已关闭")
        else:
            self._timer.start()
            self._timer_enabled = True
            self._btn_toggle.configure(text="● 关闭", bg=COLORS["switch_on"],
                                       activebackground=COLORS["switch_off"])
            self._lbl_timer_status.configure(text="定时备份: 运行中", fg="#a7f3d0")
            self._set_status("定时备份已开启")

    # ==================================================================
    # 设置
    # ==================================================================

    def _open_settings(self) -> None:
        SettingsDialog(self.root, self._settings_store, self._resolver)
        # 设置可能改变了 <HOME>，刷新列表以更新路径显示
        self._list_frame.set_configs(self._configs)
        self._set_status("设置已更新")

    # ==================================================================
    # 状态栏（线程安全）
    # ==================================================================

    def _push_status(self, msg: str) -> None:
        """线程安全的状态更新。"""
        self.root.after(0, lambda: self._set_status(msg))

    def _set_status(self, msg: str) -> None:
        self._lbl_status.configure(text=msg)

    # ==================================================================
    # 自动备份回调
    # ==================================================================

    def _on_timer_config_changed(self) -> None:
        """自动备份更新了磁盘上的配置（指纹/时间戳），重新加载。"""
        self.root.after(0, self._reload_from_disk_and_refresh)

    def _reload_from_disk_and_refresh(self) -> None:
        """从磁盘重新加载配置并刷新 UI。"""
        self._configs = self._config_store.load()
        self._list_frame.set_configs(self._configs)

    # ==================================================================
    # 退出
    # ==================================================================

    def _on_close(self) -> None:
        if self._timer.is_running:
            self._timer.stop()
        # 确保配置已持久化
        self._config_store.save(self._configs)
        self.root.destroy()
