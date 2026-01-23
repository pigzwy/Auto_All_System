#!/usr/bin/env python3
"""
GeekezBrowser 版 Google 安全设置 GUI
适配 P工具箱，使用 GeekezBrowser API

功能：
- 修改 2FA 密钥
- 修改辅助邮箱
- 获取备份验证码
- 一键修改全部
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QTextEdit,
    QSpinBox,
    QLineEdit,
    QComboBox,
    QFormLayout,
    QDialog,
)

# 路径设置
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parents[1]

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from geek_process import GeekProcess, load_accounts
from geek_security import GeekSecurityAutomation


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(os.path.dirname(sys.executable))
    return REPO_ROOT


class SecurityWorkerThread(QThread):
    """安全设置工作线程"""

    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, str, str)  # email, status, message
    finished_signal = pyqtSignal(dict)

    def __init__(
        self,
        mode: str,  # "2fa", "recovery", "backup", "one_click"
        selected_accounts: List[Dict[str, str]],
        recovery_emails: List[str],
        thread_count: int = 1,
        host: str = "127.0.0.1",
        port: int = 19527,
    ) -> None:
        super().__init__()
        self.mode = mode
        self.selected_accounts = selected_accounts
        self.recovery_emails = recovery_emails
        self.thread_count = thread_count
        self.host = host
        self.port = port
        self.is_running = True
        self.results: List[Dict[str, Any]] = []

    def stop(self) -> None:
        self.is_running = False

    def _log(self, msg: str) -> None:
        self.log_signal.emit(str(msg))

    def run(self) -> None:
        try:
            automation = GeekSecurityAutomation(host=self.host, port=self.port)

            # 检查浏览器是否运行
            if not automation.proc.api.is_running():
                self.finished_signal.emit(
                    {"success": False, "error": "GeekezBrowser 未运行，请先启动引擎"}
                )
                return

            def process_one(idx: int, account: Dict[str, str]) -> Dict[str, Any]:
                email = account.get("email", "")
                result = {"email": email, "success": False, "message": ""}

                if not self.is_running:
                    result["message"] = "已取消"
                    return result

                self._log(f"[{idx + 1}/{len(self.selected_accounts)}] 处理: {email}")

                def log_cb(msg: str):
                    self._log(f"[{email}] {msg}")

                try:
                    if self.mode == "2fa":
                        ok, new_secret, msg = automation.change_2fa_secret(
                            email, account, log_callback=log_cb
                        )
                        result["success"] = ok
                        result["new_secret"] = new_secret
                        result["message"] = msg

                        if ok and new_secret:
                            self._save_new_2fa(email, account, new_secret)

                    elif self.mode == "recovery":
                        # 获取对应的新辅助邮箱
                        new_email = ""
                        if self.recovery_emails:
                            new_email = self.recovery_emails[
                                idx % len(self.recovery_emails)
                            ]

                        if not new_email:
                            result["message"] = "无辅助邮箱"
                            return result

                        ok, msg = automation.change_recovery_email(
                            email, account, new_email, log_callback=log_cb
                        )
                        result["success"] = ok
                        result["message"] = msg

                    elif self.mode == "backup":
                        ok, codes, msg = automation.get_backup_codes(
                            email, account, log_callback=log_cb
                        )
                        result["success"] = ok
                        result["codes"] = codes
                        result["message"] = msg

                        if ok and codes:
                            self._save_backup_codes(email, codes)

                    elif self.mode == "one_click":
                        new_email = ""
                        if self.recovery_emails:
                            new_email = self.recovery_emails[
                                idx % len(self.recovery_emails)
                            ]

                        res = automation.one_click_security_update(
                            email, account, new_email, log_callback=log_cb
                        )

                        # 解析结果
                        tfa_ok, new_secret, tfa_msg = res.get("2fa", (False, "", ""))
                        rec_ok, rec_msg = res.get("recovery", (False, ""))
                        bak_ok, codes, bak_msg = res.get("backup", (False, [], ""))

                        result["success"] = tfa_ok or rec_ok or bak_ok
                        result["new_secret"] = new_secret
                        result["codes"] = codes
                        result["message"] = (
                            f"2FA:{tfa_msg}, Recovery:{rec_msg}, Backup:{bak_msg}"
                        )

                        if tfa_ok and new_secret:
                            self._save_new_2fa(email, account, new_secret)
                        if bak_ok and codes:
                            self._save_backup_codes(email, codes)

                    status = "✅" if result["success"] else "❌"
                    self.progress_signal.emit(email, status, result["message"])

                except Exception as e:
                    result["message"] = str(e)
                    self.progress_signal.emit(email, "❌", str(e))

                return result

            # 串行处理（安全设置操作建议串行，避免并发问题）
            for idx, account in enumerate(self.selected_accounts):
                if not self.is_running:
                    break
                res = process_one(idx, account)
                self.results.append(res)

            self.finished_signal.emit({"success": True, "results": self.results})

        except Exception as e:
            self._log(f"❌ 工作线程错误: {e}")
            self.finished_signal.emit({"success": False, "error": str(e)})

    def _save_new_2fa(
        self, email: str, account: Dict[str, str], new_secret: str
    ) -> None:
        """保存新 2FA 密钥到文件"""
        try:
            file_path = _base_dir() / "2dev" / "new_2fa_secrets.txt"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 构建新行: email----password----backup_email----new_secret
            line = f"{email}----{account.get('password', '')}----{account.get('backup_email', '')}----{new_secret}\n"

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)

            self._log(f"[{email}] 新密钥已保存到 new_2fa_secrets.txt")
        except Exception as e:
            self._log(f"[{email}] 保存密钥失败: {e}")

    def _save_backup_codes(self, email: str, codes: List[str]) -> None:
        """保存备份验证码到文件"""
        try:
            file_path = _base_dir() / "2dev" / "backup_codes.txt"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            codes_str = ",".join(codes)
            line = f"{email}: {codes_str}\n"

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line)

            self._log(f"[{email}] 备份验证码已保存到 backup_codes.txt")
        except Exception as e:
            self._log(f"[{email}] 保存验证码失败: {e}")


class GeekSecurityWindow(QWidget):
    """Google 安全设置窗口 (GeekezBrowser 版)"""

    def __init__(self, host: str = "127.0.0.1", port: int = 19527) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.worker: Optional[SecurityWorkerThread] = None
        self.accounts: List[Dict[str, str]] = []
        self.recovery_emails: List[str] = []

        self._init_ui()
        self._load_accounts()
        self._load_recovery_emails()

    def _init_ui(self) -> None:
        self.setWindowTitle("🔐 Google 安全设置修改 (Geek版)")
        self.setMinimumSize(900, 700)

        # 深色主题
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
            QGroupBox { border: 1px solid #333; margin-top: 8px; padding-top: 10px; font-weight: bold; color: #aaa; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
            QLineEdit, QSpinBox, QComboBox { background-color: #2d2d2d; border: 1px solid #444; border-radius: 4px; color: #fff; padding: 4px; }
            QTextEdit { background-color: #1e1e1e; border: 1px solid #333; color: #ddd; }
            QCheckBox { color: #ddd; }
            QHeaderView::section { background-color: #252525; color: #ddd; border: none; padding: 5px; font-weight: bold; }
            QTableWidget { background-color: #1e1e1e; alternate-background-color: #252525; gridline-color: #333; border: 1px solid #333; }
            QTableWidget::item:selected { background-color: #3d3d3d; color: white; }
            QPushButton { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #3d3d3d; border-radius: 4px; padding: 8px 15px; }
            QPushButton:hover { background-color: #3d3d3d; border-color: #555; }
            QPushButton:disabled { background-color: #1a1a1a; color: #666; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 标题
        title = QLabel("🔐 Google 安全设置批量修改")
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #fff; padding: 10px 0;"
        )
        layout.addWidget(title)

        # 操作模式选择
        mode_group = QGroupBox("操作模式")
        mode_layout = QHBoxLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            [
                "🔑 修改 2FA 密钥",
                "📧 修改辅助邮箱",
                "🔐 获取备份验证码",
                "🚀 一键修改全部",
            ]
        )
        self.mode_combo.setFixedWidth(200)
        mode_layout.addWidget(QLabel("选择操作:"))
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # 账号表格
        table_group = QGroupBox("账号列表")
        table_layout = QVBoxLayout()

        # 操作栏
        action_bar = QHBoxLayout()

        self.btn_refresh = QPushButton("🔄 刷新")
        self.btn_refresh.clicked.connect(self._load_accounts)

        self.select_all = QCheckBox("全选")
        self.select_all.stateChanged.connect(self._toggle_select_all)

        self.count_label = QLabel("账号: 0")

        action_bar.addWidget(self.btn_refresh)
        action_bar.addWidget(self.select_all)
        action_bar.addStretch()
        action_bar.addWidget(self.count_label)

        table_layout.addLayout(action_bar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选", "邮箱", "有环境", "状态", "消息"])
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

        # 辅助邮箱编辑
        recovery_group = QGroupBox("辅助邮箱列表 (用于修改辅助邮箱/一键修改)")
        recovery_layout = QVBoxLayout()

        self.recovery_text = QTextEdit()
        self.recovery_text.setPlaceholderText("每行一个辅助邮箱，按顺序分配给账号...")
        self.recovery_text.setMaximumHeight(100)
        recovery_layout.addWidget(self.recovery_text)

        recovery_hint = QLabel("提示: 留空则跳过辅助邮箱修改步骤")
        recovery_hint.setStyleSheet("color: #888; font-size: 11px;")
        recovery_layout.addWidget(recovery_hint)

        recovery_group.setLayout(recovery_layout)
        layout.addWidget(recovery_group)

        # 执行按钮
        btn_layout = QHBoxLayout()

        self.btn_start = QPushButton("▶️ 开始执行")
        self.btn_start.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 12px 30px; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #1a1a1a; color: #666; }
        """)
        self.btn_start.clicked.connect(self._start_processing)

        self.btn_stop = QPushButton("⏹️ 停止")
        self.btn_stop.setStyleSheet("""
            QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 12px 30px; }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.btn_stop.clicked.connect(self._stop_processing)
        self.btn_stop.setEnabled(False)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # 日志区域
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px; background: #000; color: #0f0;"
        )
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

    def _load_accounts(self) -> None:
        """加载账号列表"""
        try:
            self.accounts = load_accounts()
            proc = GeekProcess(host=self.host, port=self.port)
            envs = proc.list_envs(self.accounts)
            env_map = {e.email: e for e in envs}
        except Exception as e:
            self._log(f"加载账号失败: {e}")
            env_map = {}

        self.table.setRowCount(0)

        for row, acc in enumerate(self.accounts):
            email = acc.get("email", "").strip()
            if not email:
                continue

            env = env_map.get(email)
            has_profile = bool(env and env.has_profile)

            self.table.insertRow(row)

            cb = QCheckBox()
            self.table.setCellWidget(row, 0, cb)
            self.table.setItem(row, 1, QTableWidgetItem(email))
            self.table.setItem(row, 2, QTableWidgetItem("✅" if has_profile else "❌"))
            self.table.setItem(row, 3, QTableWidgetItem(""))
            self.table.setItem(row, 4, QTableWidgetItem(""))

        self.count_label.setText(f"账号: {len(self.accounts)}")

    def _load_recovery_emails(self) -> None:
        """加载辅助邮箱列表"""
        try:
            file_path = _base_dir() / "2dev" / "recovery_emails.txt"
            if file_path.exists():
                text = file_path.read_text(encoding="utf-8")
                self.recovery_text.setPlainText(text)
                self.recovery_emails = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
        except Exception as e:
            self._log(f"加载辅助邮箱失败: {e}")

    def _toggle_select_all(self, state: int) -> None:
        checked = state == Qt.CheckState.Checked.value
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(checked)

    def _get_selected_accounts(self) -> List[Dict[str, str]]:
        selected = []
        for row in range(self.table.rowCount()):
            cb = self.table.cellWidget(row, 0)
            if isinstance(cb, QCheckBox) and cb.isChecked():
                email_item = self.table.item(row, 1)
                if email_item:
                    email = email_item.text().strip()
                    # 找到对应的账号信息
                    for acc in self.accounts:
                        if acc.get("email", "").strip() == email:
                            selected.append(
                                {
                                    "email": email,
                                    "password": acc.get("password", ""),
                                    "backup_email": acc.get("backup_email", ""),
                                    "secret": acc.get("2fa_secret", ""),
                                    "2fa_secret": acc.get("2fa_secret", ""),
                                }
                            )
                            break
        return selected

    def _start_processing(self) -> None:
        selected = self._get_selected_accounts()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择账号")
            return

        # 解析辅助邮箱
        recovery_text = self.recovery_text.toPlainText()
        self.recovery_emails = [
            line.strip()
            for line in recovery_text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

        # 获取操作模式
        mode_idx = self.mode_combo.currentIndex()
        mode_map = {0: "2fa", 1: "recovery", 2: "backup", 3: "one_click"}
        mode = mode_map.get(mode_idx, "2fa")

        # 检查辅助邮箱
        if mode in ("recovery", "one_click") and not self.recovery_emails:
            if mode == "recovery":
                QMessageBox.warning(
                    self, "提示", "修改辅助邮箱需要提供新的辅助邮箱列表"
                )
                return

        self._log(f"开始处理 {len(selected)} 个账号，模式: {mode}")

        self.worker = SecurityWorkerThread(
            mode=mode,
            selected_accounts=selected,
            recovery_emails=self.recovery_emails,
            host=self.host,
            port=self.port,
        )
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self._update_row)
        self.worker.finished_signal.connect(self._on_finished)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.worker.start()

    def _stop_processing(self) -> None:
        if self.worker:
            self.worker.stop()
            self._log("正在停止...")

    def _log(self, msg: str) -> None:
        self.log_text.append(str(msg))

    def _update_row(self, email: str, status: str, message: str) -> None:
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item and item.text().strip() == email:
                self.table.setItem(row, 3, QTableWidgetItem(status))
                self.table.setItem(row, 4, QTableWidgetItem(message))
                break

    def _on_finished(self, result: Dict[str, Any]) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

        if result.get("success"):
            self._log("✅ 处理完成")
        else:
            error = result.get("error", "未知错误")
            self._log(f"❌ 处理失败: {error}")
            QMessageBox.warning(self, "错误", str(error))


def main() -> None:
    app = QApplication(sys.argv)
    win = GeekSecurityWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
