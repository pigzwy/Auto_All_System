#!/usr/bin/env python3
"""
GeekezBrowser 完整管理界面
类似 create_window_gui.py 的布局：左侧工具箱 + 右侧账号列表/日志

功能：
1. 自动启动 GeekezBrowser（通过 npm start）
2. 左侧 QToolBox 功能导航
3. 批量创建/管理环境
4. Google 专区功能（SheerLink、绑卡、全自动等）
"""

from __future__ import annotations

import subprocess
import sys
import os
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QTextEdit,
    QSpinBox,
    QToolBox,
    QSplitter,
    QFormLayout,
    QDialog,
    QDialogButtonBox,
)

# 路径设置
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# GeekezBrowser 源码路径
GEEK_SOURCE_PATH = r"D:\java\github\GeekezBrowser"
CONTROL_PORT = 19527
CONTROL_HOST = "127.0.0.1"


def safe_str(msg: Any) -> str:
    try:
        return str(msg)
    except Exception:
        return repr(msg)


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable))
    return REPO_ROOT


def ensure_data_files() -> None:
    for name in ["accounts.txt", "proxies.txt", "cards.txt"]:
        path = base_dir() / name
        if not path.exists():
            path.write_text("", encoding="utf-8")


# 导入 Geek 模块
try:
    from geek_process import GeekProcess, load_accounts, load_proxies, load_cards
    from geek_browser_api import GeekezBrowserAPI
except ImportError:
    # 如果从2dev/geek目录运行
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    from geek_process import GeekProcess, load_accounts, load_proxies, load_cards
    from geek_browser_api import GeekezBrowserAPI


class AppLauncher:
    """GeekezBrowser 应用启动器"""

    def __init__(self, source_path: str = GEEK_SOURCE_PATH, port: int = CONTROL_PORT):
        self.source_path = source_path
        self.port = port
        self.process: Optional[subprocess.Popen] = None
        self.api = GeekezBrowserAPI(host=CONTROL_HOST, port=port)

    def is_running(self) -> bool:
        return self.api.is_running()

    def enable_remote_debugging(self) -> None:
        self.api.enable_remote_debugging()

    def start(self, log_callback=None) -> bool:
        """启动 GeekezBrowser，返回是否成功"""
        if self.is_running():
            if log_callback:
                log_callback("[Geek] 应用已在运行")
            return True

        # 启用远程调试
        self.enable_remote_debugging()

        if log_callback:
            log_callback(f"[Geek] 启动源码版应用: {self.source_path}")
            log_callback(f"[Geek] 控制端口: {self.port}")

        try:
            npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
            creationflags = 0
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                [npm_cmd, "start", "--", f"--control-port={self.port}"],
                cwd=self.source_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                creationflags=creationflags,
            )

            if log_callback:
                log_callback("[Geek] 等待应用启动...")

            # 等待最多30秒
            for i in range(30):
                if self.is_running():
                    if log_callback:
                        log_callback(f"[Geek] OK 应用已就绪 ({i + 1}s)")
                    return True
                time.sleep(1)
                if log_callback and i > 0 and i % 5 == 0:
                    log_callback(f"[Geek] 等待中... {i}s")

            if log_callback:
                log_callback("[Geek] ERR 启动超时")
            return False

        except Exception as e:
            if log_callback:
                log_callback(f"[Geek] ERR 启动失败: {e}")
            return False

    def stop(self) -> None:
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None


class GeekWorkerThread(QThread):
    """工作线程"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, str, str)  # email, status, message
    finished_signal = pyqtSignal(dict)

    def __init__(
        self,
        task_type: str,
        selected_emails: List[str],
        api_host: str = CONTROL_HOST,
        api_port: int = CONTROL_PORT,
        api_key: str = "",
        thread_count: int = 3,
        launcher: Optional[AppLauncher] = None,
    ) -> None:
        super().__init__()
        self.task_type = task_type
        self.selected_emails = selected_emails
        self.api_host = api_host
        self.api_port = int(api_port)
        self.api_key = api_key
        self.thread_count = int(thread_count)
        self.launcher = launcher
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def _log(self, msg: str) -> None:
        self.log_signal.emit(safe_str(msg))

    def run(self) -> None:
        try:
            ensure_data_files()

            # 如果应用未运行，尝试启动
            proc = GeekProcess(host=self.api_host, port=self.api_port)
            if not proc.api.is_running():
                if self.launcher:
                    self._log("[Geek] 应用未运行，正在启动...")
                    if not self.launcher.start(log_callback=self._log):
                        self.finished_signal.emit(
                            {"success": False, "error": "启动 GeekezBrowser 失败"}
                        )
                        return
                else:
                    self.finished_signal.emit(
                        {"success": False, "error": "GeekezBrowser 未运行"}
                    )
                    return

            accounts = load_accounts()
            proxies = load_proxies()
            cards = load_cards()

            account_map = {(a.get("email") or "").strip(): a for a in accounts}

            if self.task_type == "start_app":
                if self.launcher:
                    success = self.launcher.start(log_callback=self._log)
                    self.finished_signal.emit({"success": success})
                else:
                    self.finished_signal.emit(
                        {"success": False, "error": "No launcher"}
                    )
                return

            if self.task_type == "ensure_profiles":
                self._log("[Geek] 创建/更新环境...")
                proc.ensure_profiles(
                    accounts=accounts, proxies=proxies, log_callback=self._log
                )
                self.finished_signal.emit({"success": True})
                return

            if self.task_type == "launch":
                for email in self.selected_emails:
                    if not self.is_running:
                        break
                    try:
                        launch = proc.launch_by_email(email)
                        self.progress_signal.emit(
                            email, "✅ 已启动", f"port={launch.debug_port}"
                        )
                        self._log(
                            f"[Geek] 启动成功: {email} (port={launch.debug_port})"
                        )
                    except Exception as e:
                        self.progress_signal.emit(email, "❌ 失败", safe_str(e))
                        self._log(f"[Geek] 启动失败: {email} -> {e}")
                self.finished_signal.emit({"success": True})
                return

            if self.task_type == "close":
                for email in self.selected_emails:
                    if not self.is_running:
                        break
                    try:
                        ok = proc.close_by_email(email)
                        self.progress_signal.emit(
                            email,
                            "✅ 已关闭" if ok else "⚠️",
                            "closed" if ok else "未运行",
                        )
                        self._log(f"[Geek] 关闭: {email} ({ok})")
                    except Exception as e:
                        self.progress_signal.emit(email, "❌ 失败", safe_str(e))
                        self._log(f"[Geek] 关闭失败: {email} -> {e}")
                self.finished_signal.emit({"success": True})
                return

            if self.task_type in {"sheerlink", "auto"}:
                if not self.selected_emails:
                    self.finished_signal.emit({"success": True})
                    return

                if self.task_type == "auto" and not cards:
                    self.finished_signal.emit(
                        {"success": False, "error": "cards.txt 为空"}
                    )
                    return

                def _task_one(email: str, idx: int):
                    acc = account_map.get(email)
                    if not acc:
                        return email, False, "账号未找到"

                    if self.task_type == "sheerlink":
                        ok, msg = proc.run_sheerlink(
                            acc, proxy_str=None, log_callback=self._log
                        )
                        return email, ok, msg

                    card = cards[idx % len(cards)]
                    ok, msg = proc.run_auto(
                        acc,
                        card=card,
                        api_key=self.api_key,
                        proxy_str=None,
                        log_callback=self._log,
                    )
                    return email, ok, msg

                max_workers = max(1, self.thread_count)
                self._log(f"[Geek] 开始 {self.task_type}，线程数={max_workers}")

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(_task_one, email, idx): email
                        for idx, email in enumerate(self.selected_emails)
                    }
                    for future in as_completed(futures):
                        if not self.is_running:
                            break
                        email = futures[future]
                        try:
                            _email, ok, msg = future.result()
                            self.progress_signal.emit(
                                _email, "✅" if ok else "❌", safe_str(msg)
                            )
                        except Exception as e:
                            self.progress_signal.emit(email, "❌", safe_str(e))
                            self._log(f"[Geek] 错误: {email} -> {e}")
                self.finished_signal.emit({"success": True})
                return

            self.finished_signal.emit(
                {"success": False, "error": f"未知任务: {self.task_type}"}
            )
        except Exception as e:
            self._log(f"❌ 工作线程错误: {e}")
            import traceback

            traceback.print_exc()
            self.finished_signal.emit({"success": False, "error": safe_str(e)})


class DataEditorDialog(QDialog):
    """数据编辑对话框"""

    def __init__(self, parent, title: str, file_name: str, format_hint: str):
        super().__init__(parent)
        self.file_name = file_name
        self.setWindowTitle(title)
        self.setMinimumSize(600, 500)
        self._init_ui(format_hint)
        self._load_data()

    def _init_ui(self, format_hint: str):
        layout = QVBoxLayout()

        hint = QLabel(format_hint)
        hint.setStyleSheet(
            "color: #666; padding: 5px; background: #f5f5f5; border-radius: 3px;"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("每行一条数据...")
        self.text_edit.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(self.text_edit)

        self.count_label = QLabel("行数: 0")
        self.text_edit.textChanged.connect(self._update_count)
        layout.addWidget(self.count_label)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("💾 保存")
        save_btn.setStyleSheet(
            "background: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        save_btn.clicked.connect(self._save_data)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _update_count(self):
        text = self.text_edit.toPlainText()
        lines = [
            l for l in text.split("\n") if l.strip() and not l.strip().startswith("#")
        ]
        self.count_label.setText(f"有效行数: {len(lines)}")

    def _get_file_path(self) -> Path:
        return base_dir() / self.file_name

    def _load_data(self):
        path = self._get_file_path()
        try:
            if path.exists():
                self.text_edit.setText(path.read_text(encoding="utf-8"))
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载失败: {e}")

    def _save_data(self):
        path = self._get_file_path()
        try:
            path.write_text(self.text_edit.toPlainText(), encoding="utf-8")
            QMessageBox.information(self, "成功", f"已保存到 {self.file_name}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")


class GeekezBrowserMainWindow(QMainWindow):
    """GeekezBrowser 完整管理界面"""

    def __init__(self) -> None:
        super().__init__()
        self.worker: Optional[GeekWorkerThread] = None
        self.launcher = AppLauncher()
        self.accounts: List[Dict[str, Any]] = []
        self.email_row: Dict[str, int] = {}

        ensure_data_files()
        self._init_ui()
        self._check_app_status()
        self.refresh_list()

    def _init_ui(self) -> None:
        self.setWindowTitle("🧩 GeekezBrowser 管理工具")
        self.setGeometry(100, 80, 1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ========== 左侧：功能工具箱 ==========
        left_panel = QWidget()
        left_panel.setFixedWidth(260)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)

        # 标题
        title = QLabel("🔥 功能工具箱")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 10px; background: #f0f0f0;"
        )
        left_layout.addWidget(title)

        # 工具箱
        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet("""
            QToolBox::tab {
                background: #e1e1e1;
                border-radius: 5px;
                color: #555;
                font-weight: bold;
            }
            QToolBox::tab:selected {
                background: #d0d0d0;
                color: black;
            }
        """)
        left_layout.addWidget(self.toolbox)

        # --- 应用控制分区 ---
        app_page = QWidget()
        app_layout = QVBoxLayout()
        app_layout.setContentsMargins(5, 10, 5, 10)

        self.btn_start_app = QPushButton("🚀 启动 GeekezBrowser")
        self.btn_start_app.setFixedHeight(45)
        self.btn_start_app.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold; 
                         color: white; background: #4CAF50; border-radius: 5px; }
            QPushButton:hover { background: #45a049; }
        """)
        self.btn_start_app.clicked.connect(self.action_start_app)
        app_layout.addWidget(self.btn_start_app)

        self.status_label = QLabel("状态: 检测中...")
        self.status_label.setStyleSheet("padding: 5px; font-size: 12px;")
        app_layout.addWidget(self.status_label)

        app_layout.addStretch()
        app_page.setLayout(app_layout)
        self.toolbox.addItem(app_page, "⚙️ 应用控制")

        # --- 环境管理分区 ---
        env_page = QWidget()
        env_layout = QVBoxLayout()
        env_layout.setContentsMargins(5, 10, 5, 10)

        self.btn_ensure = QPushButton("📦 创建/更新环境")
        self.btn_ensure.setFixedHeight(40)
        self.btn_ensure.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #2196F3; border-radius: 5px; }
            QPushButton:hover { background: #1976D2; }
        """)
        self.btn_ensure.clicked.connect(lambda: self.start_task("ensure_profiles"))
        env_layout.addWidget(self.btn_ensure)

        self.btn_launch = QPushButton("▶️ 启动选中浏览器")
        self.btn_launch.setFixedHeight(40)
        self.btn_launch.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #FF9800; border-radius: 5px; }
            QPushButton:hover { background: #F57C00; }
        """)
        self.btn_launch.clicked.connect(lambda: self.start_task("launch"))
        env_layout.addWidget(self.btn_launch)

        self.btn_close = QPushButton("⏹️ 关闭选中浏览器")
        self.btn_close.setFixedHeight(40)
        self.btn_close.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #f44336; border-radius: 5px; }
            QPushButton:hover { background: #d32f2f; }
        """)
        self.btn_close.clicked.connect(lambda: self.start_task("close"))
        env_layout.addWidget(self.btn_close)

        env_layout.addStretch()
        env_page.setLayout(env_layout)
        self.toolbox.addItem(env_page, "🖥️ 环境管理")

        # --- Google 专区 ---
        google_page = QWidget()
        google_layout = QVBoxLayout()
        google_layout.setContentsMargins(5, 10, 5, 10)

        self.btn_sheerlink = QPushButton("🔗 获取 SheerLink")
        self.btn_sheerlink.setFixedHeight(40)
        self.btn_sheerlink.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #4CAF50; border-radius: 5px; }
            QPushButton:hover { background: #45a049; }
        """)
        self.btn_sheerlink.clicked.connect(lambda: self.start_task("sheerlink"))
        google_layout.addWidget(self.btn_sheerlink)

        self.btn_auto = QPushButton("🚀 全自动 (验证+绑卡)")
        self.btn_auto.setFixedHeight(45)
        self.btn_auto.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #9C27B0; border-radius: 5px; }
            QPushButton:hover { background: #7B1FA2; }
        """)
        self.btn_auto.clicked.connect(lambda: self.start_task("auto"))
        google_layout.addWidget(self.btn_auto)

        google_layout.addStretch()
        google_page.setLayout(google_layout)
        self.toolbox.addItem(google_page, "🔍 Google 专区")

        # --- 数据管理分区 ---
        data_page = QWidget()
        data_layout = QVBoxLayout()
        data_layout.setContentsMargins(5, 10, 5, 10)

        self.btn_edit_accounts = QPushButton("📝 编辑账号")
        self.btn_edit_accounts.setFixedHeight(40)
        self.btn_edit_accounts.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #3F51B5; border-radius: 5px; }
            QPushButton:hover { background: #303F9F; }
        """)
        self.btn_edit_accounts.clicked.connect(self.action_edit_accounts)
        data_layout.addWidget(self.btn_edit_accounts)

        self.btn_edit_proxies = QPushButton("🌐 编辑代理")
        self.btn_edit_proxies.setFixedHeight(40)
        self.btn_edit_proxies.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #009688; border-radius: 5px; }
            QPushButton:hover { background: #00796B; }
        """)
        self.btn_edit_proxies.clicked.connect(self.action_edit_proxies)
        data_layout.addWidget(self.btn_edit_proxies)

        self.btn_edit_cards = QPushButton("💳 编辑卡号")
        self.btn_edit_cards.setFixedHeight(40)
        self.btn_edit_cards.setStyleSheet("""
            QPushButton { text-align: left; padding-left: 15px; font-weight: bold;
                         color: white; background: #FF5722; border-radius: 5px; }
            QPushButton:hover { background: #E64A19; }
        """)
        self.btn_edit_cards.clicked.connect(self.action_edit_cards)
        data_layout.addWidget(self.btn_edit_cards)

        data_layout.addStretch()
        data_page.setLayout(data_layout)
        self.toolbox.addItem(data_page, "📁 数据管理")

        main_layout.addWidget(left_panel)

        # ========== 右侧：主内容区 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # 设置区域
        cfg_group = QGroupBox("运行设置")
        cfg_form = QFormLayout()

        host_port_layout = QHBoxLayout()
        self.host_input = QLineEdit(CONTROL_HOST)
        self.host_input.setFixedWidth(120)
        self.port_input = QLineEdit(str(CONTROL_PORT))
        self.port_input.setFixedWidth(80)
        host_port_layout.addWidget(QLabel("地址:"))
        host_port_layout.addWidget(self.host_input)
        host_port_layout.addWidget(QLabel("端口:"))
        host_port_layout.addWidget(self.port_input)
        host_port_layout.addStretch()
        cfg_form.addRow("控制服务:", host_port_layout)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("SheerID API Key (可选)")
        cfg_form.addRow("API Key:", self.api_key_input)

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 20)
        self.thread_spin.setValue(3)
        cfg_form.addRow("并发数:", self.thread_spin)

        cfg_group.setLayout(cfg_form)
        right_layout.addWidget(cfg_group)

        # 操作按钮行
        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 刷新列表")
        self.btn_refresh.clicked.connect(self.refresh_list)
        btn_row.addWidget(self.btn_refresh)

        self.select_all = QCheckBox("全选")
        self.select_all.stateChanged.connect(self.toggle_select_all)
        btn_row.addWidget(self.select_all)

        self.count_label = QLabel("账号: 0")
        btn_row.addWidget(self.count_label)
        btn_row.addStretch()
        right_layout.addLayout(btn_row)

        # 账号表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["选择", "邮箱", "环境", "ProfileId", "状态", "消息"]
        )
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.table)

        # 日志区域
        right_layout.addWidget(QLabel("📋 运行日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px;"
        )
        right_layout.addWidget(self.log_text)

        main_layout.addWidget(right_panel)

    def _check_app_status(self) -> None:
        """检查应用状态"""
        if self.launcher.is_running():
            self.status_label.setText("状态: ✅ 运行中")
            self.status_label.setStyleSheet(
                "padding: 5px; font-size: 12px; color: green;"
            )
        else:
            self.status_label.setText("状态: ❌ 未运行")
            self.status_label.setStyleSheet(
                "padding: 5px; font-size: 12px; color: red;"
            )

    def append_log(self, msg: str) -> None:
        self.log_text.append(safe_str(msg))

    def toggle_select_all(self, state: int) -> None:
        checked = state == Qt.CheckState.Checked.value
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(checked)

    def refresh_list(self) -> None:
        try:
            ensure_data_files()
            self.accounts = load_accounts()
            host = self.host_input.text().strip() or CONTROL_HOST
            port = int(self.port_input.text().strip() or CONTROL_PORT)
            proc = GeekProcess(host=host, port=port)
            envs = proc.list_envs(self.accounts)
            env_map = {e.email: e for e in envs}
        except Exception as e:
            self.append_log(f"刷新失败: {e}")
            env_map = {}

        self.table.setRowCount(0)
        self.email_row.clear()

        for row, acc in enumerate(self.accounts):
            email = (acc.get("email") or "").strip()
            if not email:
                continue

            env = env_map.get(email)
            has_profile = bool(env and env.has_profile)
            profile_id = env.profile_id if env else ""

            self.table.insertRow(row)
            cb = QCheckBox()
            self.table.setCellWidget(row, 0, cb)

            self.table.setItem(row, 1, QTableWidgetItem(email))
            self.table.setItem(row, 2, QTableWidgetItem("✅" if has_profile else "❌"))
            self.table.setItem(row, 3, QTableWidgetItem(profile_id or ""))
            self.table.setItem(row, 4, QTableWidgetItem(""))
            self.table.setItem(row, 5, QTableWidgetItem(""))

            self.email_row[email] = row

        self.count_label.setText(f"账号: {len(self.email_row)}")
        self._check_app_status()

    def _selected_emails(self) -> List[str]:
        emails: List[str] = []
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, 0)
            if isinstance(cb, QCheckBox) and cb.isChecked():
                item = self.table.item(row, 1)
                if item:
                    email = item.text().strip()
                    if email:
                        emails.append(email)
        return emails

    def action_start_app(self) -> None:
        self.start_task("start_app")

    def action_edit_accounts(self) -> None:
        dlg = DataEditorDialog(
            self,
            "编辑账号",
            "accounts.txt",
            "格式: 邮箱----密码----辅助邮箱----2FA密钥",
        )
        if dlg.exec():
            self.refresh_list()

    def action_edit_proxies(self) -> None:
        dlg = DataEditorDialog(
            self,
            "编辑代理",
            "proxies.txt",
            "格式: socks5://user:pass@host:port 或 http://user:pass@host:port",
        )
        if dlg.exec():
            self.refresh_list()

    def action_edit_cards(self) -> None:
        dlg = DataEditorDialog(
            self, "编辑卡号", "cards.txt", "格式: 卡号 月份 年份 CVV（空格分隔）"
        )
        if dlg.exec():
            self.refresh_list()

    def start_task(self, task_type: str) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "提示", "任务正在运行")
            return

        selected = self._selected_emails()
        if task_type not in {"ensure_profiles", "start_app"} and not selected:
            QMessageBox.information(self, "提示", "请先勾选账号")
            return

        host = self.host_input.text().strip() or CONTROL_HOST
        try:
            port = int(self.port_input.text().strip() or CONTROL_PORT)
        except Exception:
            QMessageBox.warning(self, "错误", "端口格式不正确")
            return

        api_key = self.api_key_input.text().strip()
        thread_count = int(self.thread_spin.value())

        self.worker = GeekWorkerThread(
            task_type=task_type,
            selected_emails=selected,
            api_host=host,
            api_port=port,
            api_key=api_key,
            thread_count=thread_count,
            launcher=self.launcher,
        )
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_row_status)
        self.worker.finished_signal.connect(self.on_finished)

        self._set_buttons_enabled(False)
        self.append_log(f"\n{'=' * 40}\n开始任务: {task_type}\n{'=' * 40}")
        self.worker.start()

    def update_row_status(self, email: str, status: str, message: str) -> None:
        row = self.email_row.get(email)
        if row is None:
            return
        self.table.setItem(row, 4, QTableWidgetItem(safe_str(status)))
        self.table.setItem(row, 5, QTableWidgetItem(safe_str(message)))

    def on_finished(self, result: Dict[str, Any]) -> None:
        self._set_buttons_enabled(True)
        ok = bool(result.get("success"))
        if not ok:
            self.append_log(f"❌ 失败: {result.get('error')}")
            QMessageBox.warning(self, "任务失败", safe_str(result.get("error")))
        else:
            self.append_log("✅ 完成")
        self.refresh_list()

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for btn in [
            self.btn_refresh,
            self.btn_start_app,
            self.btn_ensure,
            self.btn_launch,
            self.btn_close,
            self.btn_sheerlink,
            self.btn_auto,
            self.btn_edit_accounts,
            self.btn_edit_proxies,
            self.btn_edit_cards,
        ]:
            btn.setEnabled(enabled)


def main() -> None:
    ensure_data_files()
    app = QApplication(sys.argv)
    win = GeekezBrowserMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
