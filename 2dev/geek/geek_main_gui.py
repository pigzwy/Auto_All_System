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
import logging
import threading
from collections import deque
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


# Thread-local storage for current email context (used by stdout/stderr capture)
_thread_local = threading.local()


def _get_current_email() -> str:
    """获取当前线程的 email 上下文"""
    return getattr(_thread_local, "current_email", "")


def _set_current_email(email: str) -> None:
    """设置当前线程的 email 上下文"""
    _thread_local.current_email = email


class _QtStreamForwarder:
    """Forward stdout/stderr writes into a callback, line-buffered.

    Automatically includes the current thread's email context.
    """

    def __init__(self, emit_line):
        """emit_line signature: (email: str, line: str) -> None"""
        self._emit_line = emit_line
        self._buf = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        text = safe_str(s)
        self._buf += text

        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.rstrip("\r")
            if line.strip():
                email = _get_current_email()
                self._emit_line(email, line)
        return len(text)

    def flush(self) -> None:
        if self._buf.strip():
            email = _get_current_email()
            self._emit_line(email, self._buf.rstrip("\r"))
        self._buf = ""

    def isatty(self) -> bool:
        return False


class _QtLogHandler(logging.Handler):
    """Forward python logging records into a callback.

    Automatically includes the current thread's email context.
    """

    def __init__(self, emit_line):
        """emit_line signature: (email: str, line: str) -> None"""
        super().__init__()
        self._emit_line = emit_line

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        if msg and str(msg).strip():
            email = _get_current_email()
            self._emit_line(email, str(msg))


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
        # Prefer graceful shutdown via control server.
        if self.api.is_running():
            try:
                self.api.shutdown()
            except Exception:
                pass

        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
            try:
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        # Best-effort wait until /health goes down.
        try:
            self.api.wait_until_down(timeout_seconds=10)
        except Exception:
            pass


class GeekWorkerThread(QThread):
    """工作线程"""

    log_signal = pyqtSignal(str, str)  # (email, line) - email 为空表示全局日志
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

    def _log(self, msg: str, email: str = "") -> None:
        """发送日志信号，email 为空表示全局日志"""
        self.log_signal.emit(email, safe_str(msg))

    def _make_log_callback(self, email: str):
        """创建带 email 上下文的 log callback，用于传给底层模块。

        同时设置 thread-local email，这样 print() 输出也能被归到对应账号。
        """

        def log_cb(msg: str) -> None:
            _set_current_email(email)
            self._log(msg, email)

        return log_cb

    def _emit_log(self, email: str, line: str) -> None:
        """用于 stdout/stderr 捕获的回调"""
        self.log_signal.emit(email, safe_str(line))

    def run(self) -> None:
        # Many modules in this repo use `print()` for progress (DB export, login steps, etc.).
        # Capture stdout/stderr inside worker thread so these logs appear in the GUI.
        # The _QtStreamForwarder now uses thread-local email context.
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr
        sys.stdout = _QtStreamForwarder(self._emit_log)
        sys.stderr = _QtStreamForwarder(self._emit_log)

        root_logger = logging.getLogger()
        handler = _QtLogHandler(self._emit_log)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root_logger.addHandler(handler)

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
                    _set_current_email(email)
                    try:
                        launch = proc.launch_by_email(email)
                        self.progress_signal.emit(
                            email, "✅ 已启动", f"port={launch.debug_port}"
                        )
                        self._log(
                            f"[Geek] 启动成功: {email} (port={launch.debug_port})",
                            email,
                        )
                    except Exception as e:
                        self.progress_signal.emit(email, "❌ 失败", safe_str(e))
                        self._log(f"[Geek] 启动失败: {email} -> {e}", email)
                _set_current_email("")
                self.finished_signal.emit({"success": True})
                return

            if self.task_type == "close":
                for email in self.selected_emails:
                    if not self.is_running:
                        break
                    _set_current_email(email)
                    try:
                        ok = proc.close_by_email(email)
                        self.progress_signal.emit(
                            email,
                            "✅ 已关闭" if ok else "⚠️",
                            "closed" if ok else "未运行",
                        )
                        self._log(f"[Geek] 关闭: {email} ({ok})", email)
                    except Exception as e:
                        self.progress_signal.emit(email, "❌ 失败", safe_str(e))
                        self._log(f"[Geek] 关闭失败: {email} -> {e}", email)
                _set_current_email("")
                self.finished_signal.emit({"success": True})
                return

            if self.task_type in {"sheerlink", "auto", "bind"}:
                if not self.selected_emails:
                    self.finished_signal.emit({"success": True})
                    return

                if self.task_type in {"auto", "bind"} and not cards:
                    self.finished_signal.emit(
                        {"success": False, "error": "cards.txt 为空"}
                    )
                    return

                def _task_one(email: str, idx: int):
                    # Set thread-local email for print() capture
                    _set_current_email(email)

                    acc = account_map.get(email)
                    if not acc:
                        return email, False, "账号未找到"

                    proxy_str = None
                    if proxies:
                        # Round-robin assign proxies to selected accounts.
                        try:
                            from geek_process import proxy_to_url

                            proxy_str = proxy_to_url(proxies[idx % len(proxies)])
                        except Exception:
                            proxy_str = None

                    # Create email-specific log callback
                    log_cb = self._make_log_callback(email)

                    if self.task_type == "sheerlink":
                        ok, msg = proc.run_sheerlink(
                            acc, proxy_str=proxy_str, log_callback=log_cb
                        )
                        return email, ok, msg

                    if self.task_type == "bind":
                        card = cards[idx % len(cards)]
                        ok, msg = proc.run_auto(
                            acc,
                            card=card,
                            api_key="",
                            proxy_str=proxy_str,
                            log_callback=log_cb,
                        )
                        return email, ok, msg

                    card = cards[idx % len(cards)]
                    ok, msg = proc.run_auto(
                        acc,
                        card=card,
                        api_key=self.api_key,
                        proxy_str=proxy_str,
                        log_callback=log_cb,
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
                            self._log(f"[Geek] 错误: {email} -> {e}", email)
                _set_current_email("")
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
        finally:
            try:
                root_logger.removeHandler(handler)
            except Exception:
                pass
            try:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
            except Exception:
                pass


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
            "color: #aaa; padding: 5px; background: #252525; border-radius: 3px;"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("每行一条数据...")
        self.text_edit.setStyleSheet(
            "font-family: Consolas, monospace; background: #1e1e1e; color: #eee; border: 1px solid #333;"
        )
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

    # 每个账号日志缓存的最大行数
    MAX_LOG_LINES = 2000

    def __init__(self) -> None:
        super().__init__()
        self.worker: Optional[GeekWorkerThread] = None
        self.launcher = AppLauncher()
        self.accounts: List[Dict[str, Any]] = []
        self.email_row: Dict[str, int] = {}

        # Best-effort local state for per-row start/stop buttons.
        # GeekezBrowser does not expose a "list running profiles" HTTP endpoint yet.
        self._running_envs: set[str] = set()

        # 日志缓存
        self._global_logs: deque = deque(maxlen=self.MAX_LOG_LINES)
        self._account_logs: Dict[str, deque] = {}  # email -> deque of log lines
        self._selected_email: str = ""  # 当前选中的账号

        ensure_data_files()
        self._init_ui()
        self._check_app_status()
        self.refresh_list()

    def _init_ui(self) -> None:
        self.setWindowTitle("P工具箱")
        self.setGeometry(100, 80, 1300, 800)

        # Dark Theme Global Styles
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { border: 1px solid #333; margin-top: 8px; padding-top: 10px; font-weight: bold; color: #aaa; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLineEdit, QSpinBox { background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px; color: #fff; padding: 4px; }
            QTextEdit { background-color: #1e1e1e; border: 1px solid #333; color: #ddd; }
            QCheckBox { color: #ddd; }
            QHeaderView::section { background-color: #252525; color: #ddd; border: none; padding: 5px; font-weight: bold; border-right: 1px solid #333; }
            QTableWidget { background-color: #1e1e1e; alternate-background-color: #252525; gridline-color: #333; border: 1px solid #333; }
            QTableWidget::item:selected { background-color: #3d3d3d; color: white; }
            QScrollBar:vertical { border: none; background: #121212; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QPushButton { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #3d3d3d; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background-color: #3d3d3d; border-color: #555; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """)

        central = QWidget()
        self.setCentralWidget(central)

        # Root Layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== 1. Top Control Bar ==========
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet(
            "background-color: #181818; border-bottom: 1px solid #333;"
        )
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)

        # Title
        title_label = QLabel("🚀 P工具箱")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #fff; letter-spacing: 1px;")
        top_layout.addWidget(title_label)

        top_layout.addStretch()

        # Engine Control
        self.status_icon = QLabel("⚫")
        self.status_label = QLabel("检测中...")
        self.status_label.setStyleSheet(
            "color: #666; font-weight: bold; margin-right: 10px;"
        )

        self.btn_engine_toggle = QPushButton("启动引擎")
        self.btn_engine_toggle.setCheckable(True)
        self.btn_engine_toggle.setFixedSize(110, 36)
        self.btn_engine_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_engine_toggle.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; color: white; border: none;
                border-radius: 18px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:checked { background-color: #f44336; }
            QPushButton:checked:hover { background-color: #d32f2f; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.btn_engine_toggle.clicked.connect(self.toggle_engine)

        top_layout.addWidget(self.status_icon)
        top_layout.addWidget(self.status_label)
        top_layout.addWidget(self.btn_engine_toggle)

        main_layout.addWidget(top_bar)

        # ========== 2. Main Body ==========
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(10, 10, 10, 10)
        body_layout.setSpacing(10)

        # --- Left: Toolbox ---
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        tb_header = QLabel("🔥 功能工具箱")
        tb_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb_header.setStyleSheet(
            "font-size: 13px; font-weight: bold; padding: 8px; background: #252525; color: #eee; border-radius: 4px;"
        )
        left_layout.addWidget(tb_header)

        self.toolbox = QToolBox()
        self.toolbox.setStyleSheet("""
            QToolBox::tab {
                background: #2d2d2d; border-radius: 4px; color: #bbb; font-weight: bold; border: 1px solid #333;
            }
            QToolBox::tab:selected { background: #3d3d3d; color: white; border-left: 3px solid #4CAF50; }
        """)

        self._add_google_section()
        self._add_data_section()

        left_layout.addWidget(self.toolbox)
        body_layout.addWidget(left_panel)

        # --- Center: Workspace ---
        workspace_panel = QWidget()
        workspace_layout = QVBoxLayout(workspace_panel)
        workspace_layout.setContentsMargins(0, 0, 0, 0)

        # Config
        cfg_group = QGroupBox("运行设置")
        cfg_layout = QHBoxLayout()
        cfg_layout.setContentsMargins(10, 10, 10, 10)

        host_layout = QHBoxLayout()
        self.host_input = QLineEdit(CONTROL_HOST)
        self.host_input.setFixedWidth(100)
        self.port_input = QLineEdit(str(CONTROL_PORT))
        self.port_input.setFixedWidth(60)
        host_layout.addWidget(QLabel("Addr:"))
        host_layout.addWidget(self.host_input)
        host_layout.addWidget(QLabel(":"))
        host_layout.addWidget(self.port_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("SheerID API Key (可选)")

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 20)
        self.thread_spin.setValue(3)
        self.thread_spin.setPrefix("并发: ")

        cfg_layout.addLayout(host_layout)
        cfg_layout.addWidget(self.api_key_input)
        cfg_layout.addWidget(self.thread_spin)
        cfg_group.setLayout(cfg_layout)

        workspace_layout.addWidget(cfg_group)

        # Action Bar
        action_bar = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_list)

        self.select_all = QCheckBox("全选")
        self.select_all.stateChanged.connect(self.toggle_select_all)

        self.count_label = QLabel("账号: 0")

        # Batch Buttons
        self.btn_batch_start = QPushButton("▶️ 批量启动")
        self.btn_batch_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_start.clicked.connect(lambda: self.start_task("launch"))

        self.btn_batch_stop = QPushButton("⏹️ 批量关闭")
        self.btn_batch_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_batch_stop.clicked.connect(lambda: self.start_task("close"))

        action_bar.addWidget(self.btn_refresh)
        action_bar.addWidget(self.select_all)
        action_bar.addSpacing(10)
        action_bar.addWidget(self.btn_batch_start)
        action_bar.addWidget(self.btn_batch_stop)
        action_bar.addStretch()
        action_bar.addWidget(self.count_label)

        workspace_layout.addLayout(action_bar)

        # ---- Table + Account Log Splitter ----
        table_log_splitter = QSplitter(Qt.Orientation.Vertical)
        table_log_splitter.setStyleSheet("""
            QSplitter::handle { background: #333; height: 3px; }
            QSplitter::handle:hover { background: #4CAF50; }
        """)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["选", "邮箱", "操作", "环境", "ID", "状态", "消息"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(
            "selection-background-color: #3d3d3d; selection-color: white;"
        )
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        # Connect table selection change
        self.table.itemSelectionChanged.connect(self.on_account_selected)

        table_log_splitter.addWidget(self.table)

        # Account Log Panel (bottom of splitter)
        account_log_panel = QWidget()
        account_log_layout = QVBoxLayout(account_log_panel)
        account_log_layout.setContentsMargins(0, 5, 0, 0)
        account_log_layout.setSpacing(3)

        self.account_log_title = QLabel("📝 账号日志: (点击表格行查看)")
        self.account_log_title.setStyleSheet(
            "font-weight: bold; color: #aaa; padding: 2px 5px; background: #1a1a1a; border-radius: 3px;"
        )
        account_log_layout.addWidget(self.account_log_title)

        self.account_log_text = QTextEdit()
        self.account_log_text.setReadOnly(True)
        self.account_log_text.setPlaceholderText("选中账号后显示该账号的日志...")
        self.account_log_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px; background: #0a0a0a; color: #0ff; border: 1px solid #333;"
        )
        self.account_log_text.setMaximumHeight(180)
        account_log_layout.addWidget(self.account_log_text)

        table_log_splitter.addWidget(account_log_panel)

        # Set initial splitter sizes (table larger, log smaller)
        table_log_splitter.setSizes([400, 150])

        workspace_layout.addWidget(table_log_splitter)
        body_layout.addWidget(workspace_panel, stretch=1)

        # --- Right: Log Panel ---
        right_panel = QWidget()
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("📋 运行日志"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px; background: #000; color: #0f0; border: 1px solid #333;"
        )
        right_layout.addWidget(self.log_text)

        body_layout.addWidget(right_panel)

        main_layout.addWidget(body_widget)

    def _add_google_section(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(6)

        def mk_btn(text, task, color):
            btn = QPushButton(text)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left; padding-left: 10px; font-weight: bold;
                    color: {color}; background: #252525; border: 1px solid {color}; border-radius: 4px;
                }}
                QPushButton:hover {{ background: {color}; color: #121212; }}
            """)
            if task:
                btn.clicked.connect(lambda: self.start_task(task))
            return btn

        self.btn_sheerlink = mk_btn("SheerLink 获取", "sheerlink", "#81C784")
        layout.addWidget(self.btn_sheerlink)

        self.btn_bind = mk_btn("仅绑卡 (无API)", "bind", "#FFB74D")
        layout.addWidget(self.btn_bind)

        self.btn_auto = mk_btn("全自动 (验证+绑卡)", "auto", "#BA68C8")
        layout.addWidget(self.btn_auto)

        self.btn_open_sheerid = mk_btn("SheerID 批量验证", None, "#90A4AE")
        self.btn_open_sheerid.clicked.connect(self.action_open_sheerid_window)
        layout.addWidget(self.btn_open_sheerid)

        layout.addStretch()
        self.toolbox.addItem(page, "Google 专区")

    def _add_data_section(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(6)

        def mk_btn(text, slot, color):
            btn = QPushButton(text)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left; padding-left: 10px; font-weight: bold;
                    color: {color}; background: #252525; border: 1px solid {color}; border-radius: 4px;
                }}
                QPushButton:hover {{ background: {color}; color: #121212; }}
            """)
            if slot:
                btn.clicked.connect(slot)
            return btn

        # Moved "Ensure Profiles" here from Environment section
        self.btn_ensure = mk_btn(
            "环境创建/更新", lambda: self.start_task("ensure_profiles"), "#64B5F6"
        )
        layout.addWidget(self.btn_ensure)

        self.btn_edit_accounts = mk_btn(
            "账号编辑", self.action_edit_accounts, "#7986CB"
        )
        layout.addWidget(self.btn_edit_accounts)

        self.btn_edit_proxies = mk_btn("代理编辑", self.action_edit_proxies, "#4DB6AC")
        layout.addWidget(self.btn_edit_proxies)

        self.btn_edit_cards = mk_btn("卡号编辑", self.action_edit_cards, "#FF8A65")
        layout.addWidget(self.btn_edit_cards)

        layout.addStretch()
        self.toolbox.addItem(page, "📁 数据管理")

    def toggle_engine(self, checked: bool):
        if checked:
            # Start
            if not self.launcher.is_running():
                self.btn_engine_toggle.setText("启动中...")
                self.btn_engine_toggle.setEnabled(False)
                self.start_task("start_app")
            else:
                self._check_app_status()
        else:
            # Stop
            if self.launcher.is_running():
                self.btn_engine_toggle.setText("停止中...")
                self.btn_engine_toggle.setEnabled(False)

                import threading

                def _do_stop():
                    err: Optional[str] = None
                    try:
                        self.launcher.stop()
                    except Exception as e:
                        err = safe_str(e)

                    def _finish():
                        if err:
                            self.append_log(f"[Control] 停止失败: {err}")
                        else:
                            self.append_log("[Control] 引擎已停止")
                        self._check_app_status()

                    QTimer.singleShot(0, _finish)

                threading.Thread(target=_do_stop, daemon=True).start()
            else:
                self._check_app_status()

    def _check_app_status(self) -> None:
        """检查应用状态"""
        is_running = self.launcher.is_running()
        if is_running:
            self.status_label.setText("状态: ✅ 运行中")
            self.status_label.setStyleSheet(
                "color: #66bb6a; font-weight: bold; margin-right: 10px;"
            )
            self.status_icon.setText("🟢")
            self.btn_engine_toggle.setChecked(True)
            self.btn_engine_toggle.setText("停止引擎")
            self.btn_engine_toggle.setStyleSheet("""
                QPushButton { background: #d32f2f; color: white; border-radius: 18px; font-weight: bold; border: 1px solid #b71c1c; }
                QPushButton:hover { background: #b71c1c; }
            """)
        else:
            self.status_label.setText("状态: ❌ 未运行")
            self.status_label.setStyleSheet(
                "color: #ef5350; font-weight: bold; margin-right: 10px;"
            )
            self.status_icon.setText("🔴")
            self.btn_engine_toggle.setChecked(False)
            self.btn_engine_toggle.setText("启动引擎")
            self.btn_engine_toggle.setStyleSheet("""
                QPushButton { background: #388E3C; color: white; border-radius: 18px; font-weight: bold; border: 1px solid #2E7D32; }
                QPushButton:hover { background: #2E7D32; }
            """)

        self.btn_engine_toggle.setEnabled(True)

    def append_log(self, msg: str) -> None:
        """追加到全局日志（右侧面板）"""
        self.log_text.append(safe_str(msg))

    def on_worker_log(self, email: str, line: str) -> None:
        """处理 Worker 发来的日志信号，分流到全局和账号缓存"""
        line = safe_str(line)

        # 1. 始终追加到全局日志
        self._global_logs.append(line)
        self.log_text.append(line)

        # 2. 如果有 email，也追加到账号日志缓存
        if email:
            if email not in self._account_logs:
                self._account_logs[email] = deque(maxlen=self.MAX_LOG_LINES)
            self._account_logs[email].append(line)

            # 如果当前选中的就是这个账号，实时更新账号日志面板
            if email == self._selected_email:
                self.account_log_text.append(line)

    def on_account_selected(self) -> None:
        """表格选中行变化时，刷新账号日志面板"""
        selection_model = self.table.selectionModel()
        if not selection_model:
            return

        selected_rows = selection_model.selectedRows()
        if not selected_rows:
            self._selected_email = ""
            self.account_log_title.setText("📝 账号日志: (点击表格行查看)")
            self.account_log_text.clear()
            return

        row = selected_rows[0].row()
        email_item = self.table.item(row, 1)
        if not email_item:
            return

        email = email_item.text().strip()
        if not email:
            return

        self._selected_email = email
        self.account_log_title.setText(f"📝 账号日志: {email}")

        # 从缓存加载该账号的历史日志
        self.account_log_text.clear()
        if email in self._account_logs:
            logs = list(self._account_logs[email])
            self.account_log_text.setPlainText("\n".join(logs))
            # 滚动到底部
            scrollbar = self.account_log_text.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())
        else:
            self.account_log_text.setPlainText("(暂无日志)")

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

            # Action Column (New)
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(4)

            btn_play = QPushButton("▶️")
            btn_play.setFixedSize(30, 24)
            btn_play.setToolTip("启动")
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            # Use default args to capture variable
            btn_play.clicked.connect(lambda _, e=email: self.start_task("launch", [e]))

            btn_stop = QPushButton("⏹️")
            btn_stop.setFixedSize(30, 24)
            btn_stop.setToolTip("关闭")
            btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_stop.clicked.connect(lambda _, e=email: self.start_task("close", [e]))

            action_layout.addWidget(btn_play)
            action_layout.addWidget(btn_stop)
            action_layout.addStretch()
            self.table.setCellWidget(row, 2, action_widget)

            self.table.setItem(row, 3, QTableWidgetItem("✅" if has_profile else "❌"))
            self.table.setItem(row, 4, QTableWidgetItem(profile_id or ""))
            self.table.setItem(row, 5, QTableWidgetItem(""))
            self.table.setItem(row, 6, QTableWidgetItem(""))

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

    def action_open_sheerid_window(self) -> None:
        """打开现有的 SheerID 批量验证窗口（读取 sheerIDlink.txt）。"""
        try:
            from sheerid_gui import SheerIDWindow
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法加载 SheerID 工具: {e}")
            return

        dlg = SheerIDWindow(self)
        # Best-effort: sync API key from main window.
        try:
            key = self.api_key_input.text().strip()
            if key:
                dlg.api_key_input.setText(key)
        except Exception:
            pass
        dlg.exec()

    def start_task(
        self, task_type: str, specific_emails: Optional[List[str]] = None
    ) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "提示", "任务正在运行")
            return

        selected = specific_emails if specific_emails else self._selected_emails()
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
        self.worker.log_signal.connect(self.on_worker_log)
        self.worker.progress_signal.connect(self.update_row_status)
        self.worker.finished_signal.connect(self.on_finished)

        self._set_buttons_enabled(False)
        self.append_log(f"\n{'=' * 40}\n开始任务: {task_type}\n{'=' * 40}")
        self.worker.start()

    def update_row_status(self, email: str, status: str, message: str) -> None:
        row = self.email_row.get(email)
        if row is None:
            return
        # Updated columns: Status=5, Msg=6
        self.table.setItem(row, 5, QTableWidgetItem(safe_str(status)))
        self.table.setItem(row, 6, QTableWidgetItem(safe_str(message)))

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
        buttons = [
            getattr(self, "btn_refresh", None),
            getattr(self, "btn_batch_start", None),
            getattr(self, "btn_batch_stop", None),
            getattr(self, "btn_engine_toggle", None),
            getattr(self, "btn_sheerlink", None),
            getattr(self, "btn_bind", None),
            getattr(self, "btn_auto", None),
            getattr(self, "btn_open_sheerid", None),
            getattr(self, "btn_ensure", None),
            getattr(self, "btn_edit_accounts", None),
            getattr(self, "btn_edit_proxies", None),
            getattr(self, "btn_edit_cards", None),
        ]
        for btn in buttons:
            if btn is not None:
                btn.setEnabled(bool(enabled))


def main() -> None:
    ensure_data_files()
    app = QApplication(sys.argv)
    win = GeekezBrowserMainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
