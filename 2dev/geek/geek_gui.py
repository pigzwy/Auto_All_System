#!/usr/bin/env python3
"""GeekezBrowser GUI entry.

Goals (from geek_task_progress.md):
- Add a Geek GUI entry while keeping Bit flow intact
- Hide create-parameter panel (Geek uses accounts.txt as env list)

Run:
  python 2dev/geek/geek_gui.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import traceback
import sys
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def safe_str(msg: Any) -> str:
    try:
        return str(msg)
    except Exception:
        return repr(msg)


REPO_ROOT = Path(__file__).resolve().parents[2]


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable))
    return REPO_ROOT


def ensure_data_files() -> None:
    for name in ["accounts.txt", "proxies.txt", "cards.txt"]:
        path = base_dir() / name
        if not path.exists():
            path.write_text("", encoding="utf-8")


# Make repo root importable
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from geek_process import GeekProcess, load_accounts, load_proxies, load_cards


class GeekWorkerThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, str, str)  # email, status, message
    finished_signal = pyqtSignal(dict)

    def __init__(
        self,
        task_type: str,
        selected_emails: List[str],
        api_host: str,
        api_port: int,
        api_key: str,
        thread_count: int,
    ) -> None:
        super().__init__()
        self.task_type = task_type
        self.selected_emails = selected_emails
        self.api_host = api_host
        self.api_port = int(api_port)
        self.api_key = api_key
        self.thread_count = int(thread_count)
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def _log(self, msg: str) -> None:
        self.log_signal.emit(safe_str(msg))

    def run(self) -> None:
        try:
            ensure_data_files()
            proc = GeekProcess(host=self.api_host, port=self.api_port)
            accounts = load_accounts()
            proxies = load_proxies()
            cards = load_cards()

            account_map = {(a.get("email") or "").strip(): a for a in accounts}

            if self.task_type == "ensure_profiles":
                self._log("[Geek] create/update profiles...")
                proc.ensure_profiles(accounts=accounts, proxies=proxies, log_callback=self._log)
                self.finished_signal.emit({"success": True})
                return

            if self.task_type == "launch":
                for email in self.selected_emails:
                    if not self.is_running:
                        break
                    try:
                        launch = proc.launch_by_email(email)
                        self.progress_signal.emit(email, "✅ launched", f"port={launch.debug_port}")
                        self._log(f"[Geek] launched: {email} (port={launch.debug_port})")
                    except Exception as e:
                        self.progress_signal.emit(email, "❌ failed", safe_str(e))
                        self._log(f"[Geek] launch failed: {email} -> {e}")
                self.finished_signal.emit({"success": True})
                return

            if self.task_type == "close":
                for email in self.selected_emails:
                    if not self.is_running:
                        break
                    try:
                        ok = proc.close_by_email(email)
                        self.progress_signal.emit(email, "✅ closed" if ok else "⚠️", "closed" if ok else "not running")
                        self._log(f"[Geek] closed: {email} ({ok})")
                    except Exception as e:
                        self.progress_signal.emit(email, "❌ failed", safe_str(e))
                        self._log(f"[Geek] close failed: {email} -> {e}")
                self.finished_signal.emit({"success": True})
                return

            if self.task_type in {"sheerlink", "auto"}:
                if not self.selected_emails:
                    self.finished_signal.emit({"success": True})
                    return

                if self.task_type == "auto" and not cards:
                    self.finished_signal.emit({"success": False, "error": "cards.txt 为空"})
                    return

                def _task_one(email: str, idx: int):
                    acc = account_map.get(email)
                    if not acc:
                        return email, False, "account not found"

                    if self.task_type == "sheerlink":
                        ok, msg = proc.run_sheerlink(acc, proxy_str=None, log_callback=self._log)
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
                self._log(f"[Geek] start {self.task_type} with threads={max_workers}")

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
                            self.progress_signal.emit(_email, "✅" if ok else "❌", safe_str(msg))
                        except Exception as e:
                            self.progress_signal.emit(email, "❌", safe_str(e))
                            self._log(f"[Geek] worker error: {email} -> {e}")
                self.finished_signal.emit({"success": True})
                return

            self.finished_signal.emit({"success": False, "error": f"unknown task: {self.task_type}"})
        except Exception as e:
            self._log(f"❌ 工作线程错误: {e}")
            traceback.print_exc()
            self.finished_signal.emit({"success": False, "error": safe_str(e)})


class GeekezBrowserWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.worker: Optional[GeekWorkerThread] = None
        self.accounts: List[Dict[str, Any]] = []
        self.email_row: Dict[str, int] = {}

        ensure_data_files()
        self._init_ui()
        self.refresh_list()

    def _init_ui(self) -> None:
        self.setWindowTitle("GeekezBrowser 管理")
        self.setGeometry(120, 80, 1100, 780)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        title = QLabel("🧩 GeekezBrowser 管理 (accounts.txt)")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        cfg_group = QGroupBox("运行设置")
        cfg_form = QFormLayout()

        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QLineEdit("19527")
        cfg_form.addRow("控制地址:", self.host_input)
        cfg_form.addRow("控制端口:", self.port_input)

        self.api_key_input = QLineEdit("")
        self.api_key_input.setPlaceholderText("SheerID API Key (可选)")
        cfg_form.addRow("SheerID API Key:", self.api_key_input)

        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 50)
        self.thread_spin.setValue(3)
        cfg_form.addRow("并发线程:", self.thread_spin)

        cfg_group.setLayout(cfg_form)
        layout.addWidget(cfg_group)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("刷新列表")
        self.btn_refresh.clicked.connect(self.refresh_list)
        btn_row.addWidget(self.btn_refresh)

        self.btn_profiles = QPushButton("创建/更新环境")
        self.btn_profiles.clicked.connect(lambda: self.start_task("ensure_profiles"))
        btn_row.addWidget(self.btn_profiles)

        self.btn_launch = QPushButton("启动浏览器")
        self.btn_launch.clicked.connect(lambda: self.start_task("launch"))
        btn_row.addWidget(self.btn_launch)

        self.btn_close = QPushButton("关闭浏览器")
        self.btn_close.clicked.connect(lambda: self.start_task("close"))
        btn_row.addWidget(self.btn_close)

        self.btn_sheerlink = QPushButton("获取 SheerLink")
        self.btn_sheerlink.clicked.connect(lambda: self.start_task("sheerlink"))
        btn_row.addWidget(self.btn_sheerlink)

        self.btn_auto = QPushButton("全自动(验证+绑卡)")
        self.btn_auto.clicked.connect(lambda: self.start_task("auto"))
        self.btn_auto.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_row.addWidget(self.btn_auto)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Select all
        sel_row = QHBoxLayout()
        self.select_all = QCheckBox("全选/取消全选")
        self.select_all.stateChanged.connect(self.toggle_select_all)
        sel_row.addWidget(self.select_all)

        self.count_label = QLabel("账号: 0")
        sel_row.addWidget(self.count_label)
        sel_row.addStretch()
        layout.addLayout(sel_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["选择", "邮箱", "Profile", "ProfileId", "状态", "消息"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Log
        layout.addWidget(QLabel("运行日志:"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        layout.addWidget(self.log_text)

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
            host = self.host_input.text().strip() or "127.0.0.1"
            port = int(self.port_input.text().strip() or "19527")
            proc = GeekProcess(host=host, port=port)
            envs = proc.list_envs(self.accounts)
            env_map = {e.email: e for e in envs}
        except Exception as e:
            QMessageBox.warning(self, "错误", f"刷新失败: {e}")
            return

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

    def start_task(self, task_type: str) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "提示", "任务正在运行")
            return

        selected = self._selected_emails()
        if task_type not in {"ensure_profiles"} and not selected:
            QMessageBox.information(self, "提示", "请先勾选账号")
            return

        host = self.host_input.text().strip() or "127.0.0.1"
        try:
            port = int(self.port_input.text().strip() or "19527")
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
        )
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.update_row_status)
        self.worker.finished_signal.connect(self.on_finished)

        self._set_buttons_enabled(False)
        self.append_log(f"\n=== start: {task_type} ===")
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
            self.btn_profiles,
            self.btn_launch,
            self.btn_close,
            self.btn_sheerlink,
            self.btn_auto,
        ]:
            btn.setEnabled(enabled)


def main() -> None:
    ensure_data_files()
    app = QApplication(sys.argv)
    win = GeekezBrowserWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
