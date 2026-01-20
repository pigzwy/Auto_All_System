"""
Google账号安全信息修改 - GUI界面
PyQt6 实现
"""
import sys
import os
import random
import asyncio
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QTextEdit, QTableWidget,
                              QTableWidgetItem, QHeaderView, QMessageBox,
                              QCheckBox, QGroupBox, QFormLayout, QLineEdit,
                              QInputDialog, QProgressBar, QSpinBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import re


from bit_api import openBrowser, closeBrowser
from create_window import get_browser_list, get_browser_info


class SecurityWorkerThread(QThread):
    """安全修改工作线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, str, str)  # email, status, message
    finished_signal = pyqtSignal(dict)
    request_code_signal = pyqtSignal(str)  # 请求验证码信号
    
    def __init__(self, mode, accounts, recovery_emails=None):
        super().__init__()
        self.mode = mode  # "2fa" or "recovery"
        self.accounts = accounts
        self.recovery_emails = recovery_emails or []
        self.is_running = True
        self.pending_verification_code = None
        self.verification_code_received = False
    
    def stop(self):
        self.is_running = False
    
    def set_verification_code(self, code):
        """设置验证码（由GUI调用）"""
        self.pending_verification_code = code
        self.verification_code_received = True
    
    def run(self):
        import asyncio
        try:
            asyncio.run(self._process_all())
        except Exception as e:
            self.log_signal.emit(f"❌ 工作线程错误: {e}")
            import traceback
            traceback.print_exc()
        
        self.finished_signal.emit({'success': True})
    
    async def _process_all(self):
        """处理所有账号"""
        from google_security_automation import (
            change_2fa_secret, change_recovery_email, get_random_recovery_email, 
            save_new_2fa_secret, get_backup_codes, one_click_security_update
        )
        
        total = len(self.accounts)
        success_count = 0
        fail_count = 0
        
        for i, account in enumerate(self.accounts):
            if not self.is_running:
                self.log_signal.emit("⚠️ 任务已停止")
                break
            
            email = account.get('email', '')
            browser_id = account.get('browser_id', '')
            
            self.log_signal.emit(f"\n{'='*50}")
            self.log_signal.emit(f"[{i+1}/{total}] 处理账号: {email}")
            self.log_signal.emit(f"{'='*50}")
            
            try:
                if self.mode == "2fa":
                    # 修改2FA
                    success, new_secret, message = await change_2fa_secret(
                        browser_id, 
                        account,
                        log_callback=lambda msg: self.log_signal.emit(msg)
                    )
                    
                    if success:
                        # 显示完整的新密钥给用户
                        if new_secret:
                            self.log_signal.emit(f"📁 新密钥已保存到: new_2fa_secrets.txt")
                            self.log_signal.emit(f"🔑 完整新密钥: {new_secret}")
                        self.progress_signal.emit(email, "✅ 成功", f"新密钥: {new_secret}" if new_secret else message)
                        success_count += 1
                    else:
                        self.progress_signal.emit(email, "❌ 失败", message)
                        fail_count += 1
                
                elif self.mode == "recovery":
                    # 修改辅助邮箱
                    new_email = get_random_recovery_email(self.recovery_emails)
                    if not new_email:
                        self.progress_signal.emit(email, "❌ 失败", "没有可用的备用邮箱")
                        fail_count += 1
                        continue
                    
                    self.log_signal.emit(f"📧 随机选择新邮箱: {new_email}")
                    
                    # 定义验证码回调
                    async def get_verification_code(target_email):
                        self.verification_code_received = False
                        self.pending_verification_code = None
                        
                        # 发送信号请求验证码
                        self.request_code_signal.emit(target_email)
                        
                        # 等待验证码
                        timeout = 300  # 5分钟超时
                        elapsed = 0
                        while not self.verification_code_received and elapsed < timeout:
                            await asyncio.sleep(1)
                            elapsed += 1
                            if not self.is_running:
                                return None
                        
                        return self.pending_verification_code
                    
                    success, message = await change_recovery_email(
                        browser_id,
                        account,
                        new_email,
                        verification_code_callback=get_verification_code,
                        log_callback=lambda msg: self.log_signal.emit(msg)
                    )
                    
                    if success:
                        self.progress_signal.emit(email, "✅ 成功", f"新邮箱: {new_email}")
                        success_count += 1
                    else:
                        self.progress_signal.emit(email, "❌ 失败", message)
                        fail_count += 1
                
                elif self.mode == "backup_codes":
                    # 仅获取备份验证码
                    success, codes, message = await get_backup_codes(
                        browser_id,
                        account,
                        log_callback=lambda msg: self.log_signal.emit(msg)
                    )
                    
                    if success:
                        self.log_signal.emit(f"📁 备份验证码已保存到: backup_codes.txt")
                        self.log_signal.emit(f"🔐 获取到 {len(codes)} 个备份验证码")
                        self.progress_signal.emit(email, "✅ 成功", f"获取到 {len(codes)} 个备份码")
                        success_count += 1
                    else:
                        self.progress_signal.emit(email, "❌ 失败", message)
                        fail_count += 1
                
                elif self.mode == "one_click":
                    # 一键修改（2FA + 备份码 + 辅助邮箱）
                    new_email = get_random_recovery_email(self.recovery_emails) if self.recovery_emails else None
                    
                    # 定义验证码回调
                    async def get_verification_code(target_email):
                        self.verification_code_received = False
                        self.pending_verification_code = None
                        self.request_code_signal.emit(target_email)
                        
                        timeout = 300
                        elapsed = 0
                        while not self.verification_code_received and elapsed < timeout:
                            await asyncio.sleep(1)
                            elapsed += 1
                            if not self.is_running:
                                return None
                        return self.pending_verification_code
                    
                    results = await one_click_security_update(
                        browser_id,
                        account,
                        new_recovery_email=new_email,
                        verification_code_callback=get_verification_code if new_email else None,
                        log_callback=lambda msg: self.log_signal.emit(msg)
                    )
                    
                    # 统计结果
                    all_success = results['2fa']['success'] and results['backup_codes']['success']
                    if new_email:
                        all_success = all_success and results['recovery_email']['success']
                    
                    if all_success:
                        result_msg = f"2FA:✅ 备份码:✅"
                        if new_email:
                            result_msg += f" 邮箱:✅"
                        self.progress_signal.emit(email, "✅ 成功", result_msg)
                        success_count += 1
                    else:
                        result_msg = f"2FA:{'✅' if results['2fa']['success'] else '❌'} "
                        result_msg += f"备份码:{'✅' if results['backup_codes']['success'] else '❌'}"
                        if new_email:
                            result_msg += f" 邮箱:{'✅' if results['recovery_email']['success'] else '❌'}"
                        self.progress_signal.emit(email, "⚠️ 部分成功", result_msg)
                        fail_count += 1
                
            except Exception as e:
                self.progress_signal.emit(email, "❌ 错误", str(e))
                fail_count += 1
            
            # 账号间延迟
            if i < total - 1 and self.is_running:
                self.log_signal.emit("⏳ 等待5秒后处理下一个账号...")
                await asyncio.sleep(5)
        
        self.log_signal.emit(f"\n{'='*50}")
        self.log_signal.emit(f"📊 处理完成: 成功 {success_count}, 失败 {fail_count}")
        self.log_signal.emit(f"{'='*50}")


class GoogleSecurityWindow(QWidget):
    """Google安全修改窗口"""
    
    def __init__(self, mode="2fa"):
        super().__init__()
        self.mode = mode  # "2fa" or "recovery"
        self.worker = None
        self.accounts = []
        self.recovery_emails = []
        self.processed_emails = set()  # 已成功处理的账号邮箱
        
        self.initUI()
        self.load_processed_emails()  # 先加载已处理记录
        self.load_accounts()
        self.load_recovery_emails()
    
    def load_processed_emails(self):
        """从 new_2fa_secrets.txt 加载已成功处理的账号"""
        try:
            import os
            base_path = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_path, "new_2fa_secrets.txt")
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        # 格式: 时间 | 邮箱 | 密钥
                        parts = line.split('|')
                        if len(parts) >= 2:
                            email = parts[1].strip()
                            if '@' in email:
                                self.processed_emails.add(email.lower())
                
                if self.processed_emails:
                    self.log(f"📋 检测到 {len(self.processed_emails)} 个已处理的账号")
        except Exception as e:
            self.log(f"⚠️ 加载已处理记录时出错: {e}")
    
    def initUI(self):
        self.setWindowTitle("Google安全修改工具")
        self.setGeometry(100, 100, 1100, 750)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("🔐 Google账号安全修改工具")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 模式选择区域
        mode_layout = QHBoxLayout()
        mode_label = QLabel("操作模式:")
        mode_label.setFont(QFont("Microsoft YaHei", 10))
        mode_layout.addWidget(mode_label)
        
        from PyQt6.QtWidgets import QComboBox
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("🔑 修改2FA密钥", "2fa")
        self.mode_combo.addItem("📧 修改辅助邮箱", "recovery")
        self.mode_combo.addItem("🔐 获取备份验证码", "backup_codes")
        self.mode_combo.addItem("🚀 一键修改全部", "one_click")
        self.mode_combo.setMinimumWidth(200)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        
        # 设置默认模式
        for i in range(self.mode_combo.count()):
            if self.mode_combo.itemData(i) == self.mode:
                self.mode_combo.setCurrentIndex(i)
                break
        
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # 模式说明
        self.desc_label = QLabel()
        self.desc_label.setStyleSheet("color: #666; margin-bottom: 10px; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        self.update_mode_description()
        layout.addWidget(self.desc_label)
        
        # 邮箱列表信息（recovery和one_click模式显示）
        self.email_info_widget = QWidget()
        email_info_layout = QHBoxLayout(self.email_info_widget)
        email_info_layout.setContentsMargins(0, 0, 0, 0)
        self.email_count_label = QLabel("备用邮箱列表: 0 个")
        email_info_layout.addWidget(self.email_count_label)
        
        reload_email_btn = QPushButton("🔄 重新加载")
        reload_email_btn.clicked.connect(self.load_recovery_emails)
        email_info_layout.addWidget(reload_email_btn)
        email_info_layout.addStretch()
        layout.addWidget(self.email_info_widget)
        self.email_info_widget.setVisible(self.mode in ["recovery", "one_click"])
        
        # 全选复选框
        select_layout = QHBoxLayout()
        self.select_all_checkbox = QCheckBox("全选/取消全选")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        select_layout.addWidget(self.select_all_checkbox)
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        # 账号表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选择", "邮箱", "浏览器ID", "状态", "结果"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # 日志区域
        log_label = QLabel("运行日志:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton("🔄 刷新列表")
        self.btn_refresh.clicked.connect(self.load_accounts)
        button_layout.addWidget(self.btn_refresh)
        
        self.btn_start = QPushButton("▶️ 开始处理")
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        button_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton("⏹️ 停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_processing)
        button_layout.addWidget(self.btn_stop)
        
        # 标记为已处理按钮
        self.btn_mark_processed = QPushButton("✅ 标记为已处理")
        self.btn_mark_processed.clicked.connect(self.mark_as_processed)
        self.btn_mark_processed.setToolTip("将选中的账号标记为已处理（写入记录文件）")
        button_layout.addWidget(self.btn_mark_processed)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def on_mode_changed(self, index):
        """模式切换时更新界面"""
        self.mode = self.mode_combo.itemData(index)
        self.update_mode_description()
        # 显示/隐藏邮箱列表信息
        self.email_info_widget.setVisible(self.mode in ["recovery", "one_click"])
        self.log(f"📌 切换到模式: {self.mode_combo.currentText()}")
    
    def update_mode_description(self):
        """更新模式说明文本"""
        descriptions = {
            "2fa": "🔑 全自动模式：自动提取新2FA密钥并验证，无需手机扫码。新密钥保存到 new_2fa_secrets.txt",
            "recovery": "📧 半自动模式：系统随机选择新辅助邮箱，需要手动输入收到的验证码",
            "backup_codes": "🔐 全自动模式：获取账号的10个备份验证码，保存到 backup_codes.txt",
            "one_click": "🚀 一键修改模式：依次执行 2FA修改 → 获取备份码 → 修改辅助邮箱（如有备用邮箱列表）"
        }
        self.desc_label.setText(descriptions.get(self.mode, ""))
    
    def load_recovery_emails(self):
        """加载备用邮箱列表"""
        from google_security_automation import load_recovery_emails
        self.recovery_emails = load_recovery_emails()
        
        # 始终更新标签（用于recovery和one_click模式）
        self.email_count_label.setText(f"备用邮箱列表: {len(self.recovery_emails)} 个")
        
        if not self.recovery_emails:
            self.log("⚠️ 未找到 recovery_emails.txt 或文件为空")
            self.log("请在程序目录创建 recovery_emails.txt，每行一个邮箱")
        else:
            self.log(f"✅ 加载了 {len(self.recovery_emails)} 个备用邮箱")
    
    def load_accounts(self):
        """加载账号列表"""
        try:
            browsers = get_browser_list(page=0, pageSize=1000)
            
            self.table.setRowCount(0)
            self.accounts = []
            
            for browser in browsers:
                account = None
                
                # 方式1: 从 remark 字段解析（格式：邮箱---密码---辅助邮箱---2FA密钥）
                remark = browser.get('remark', '')
                if '---' in remark:
                    parts = re.split(r'-{3,}', remark)
                    if len(parts) >= 2 and '@' in parts[0]:
                        account = {
                            'email': parts[0].strip(),
                            'password': parts[1].strip() if len(parts) > 1 else '',
                            'backup': parts[2].strip() if len(parts) > 2 else '',
                            'secret': parts[3].strip() if len(parts) > 3 else '',
                            'browser_id': browser.get('id', ''),
                            'browser_name': browser.get('name', '')
                        }
                
                # 方式2: 从 userName 字段获取（BitBrowser 标准字段）
                if not account:
                    user_name = browser.get('userName', '')
                    if user_name and '@' in user_name:
                        # 密码可能经过加密，尝试从 remark 或其他字段获取
                        password = browser.get('password', '')
                        # BitBrowser 的密码字段可能加密，检查是否有明文密码格式
                        if '@' in password or len(password) > 50:  # 加密格式通常很长
                            password = ''  # 加密的密码不可用，需要从其他地方获取
                        
                        # 尝试从 remark 解析密码等信息
                        if remark:
                            # 支持简单的分隔格式
                            for sep in ['----', '---', '|||', '\t', ' ']:
                                if sep in remark:
                                    parts = remark.split(sep)
                                    parts = [p.strip() for p in parts if p.strip()]
                                    if parts:
                                        if not password and len(parts) >= 1:
                                            # 如果第一部分是邮箱，密码在第二部分
                                            if '@' in parts[0]:
                                                password = parts[1] if len(parts) > 1 else ''
                                            else:
                                                password = parts[0]
                                        break
                        
                        account = {
                            'email': user_name,
                            'password': password,
                            'backup': '',
                            'secret': browser.get('faSecretKey', '') or '',
                            'browser_id': browser.get('id', ''),
                            'browser_name': browser.get('name', '')
                        }
                
                if not account:
                    continue
                
                self.accounts.append(account)
                
                # 检查是否已处理过
                is_processed = account['email'].lower() in self.processed_emails
                
                # 添加到表格
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # 复选框 - 已处理的默认不勾选
                checkbox = QCheckBox()
                checkbox.setChecked(not is_processed)  # 未处理的才勾选
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row, 0, checkbox_widget)
                
                self.table.setItem(row, 1, QTableWidgetItem(account['email']))
                self.table.setItem(row, 2, QTableWidgetItem(account['browser_id'][:12] + "..."))
                
                # 状态列 - 标记已处理的账号，同时显示密码状态
                status_text = ""
                if is_processed:
                    status_text = "✅ 已处理"
                elif not account['password']:
                    status_text = "⚠️ 缺少密码"
                else:
                    status_text = "待处理"
                
                status_item = QTableWidgetItem(status_text)
                if is_processed:
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                elif not account['password']:
                    status_item.setForeground(Qt.GlobalColor.darkYellow)
                self.table.setItem(row, 3, status_item)
                self.table.setItem(row, 4, QTableWidgetItem(""))
            
            # 统计已处理和待处理数量
            processed_count = sum(1 for acc in self.accounts if acc['email'].lower() in self.processed_emails)
            pending_count = len(self.accounts) - processed_count
            missing_pwd = sum(1 for acc in self.accounts if not acc['password'])
            
            self.log(f"✅ 加载了 {len(self.accounts)} 个账号 (待处理: {pending_count}, 已处理: {processed_count})")
            if missing_pwd > 0:
                self.log(f"⚠️ 有 {missing_pwd} 个账号缺少密码，可能无法自动登录")
            
        except Exception as e:
            self.log(f"❌ 加载账号失败: {e}")
            import traceback
            traceback.print_exc()
    
    def toggle_select_all(self, state):
        """全选/取消全选"""
        is_checked = (state == Qt.CheckState.Checked.value)
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(is_checked)
    
    def get_selected_accounts(self):
        """获取选中的账号"""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox_widget = self.table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    if row < len(self.accounts):
                        selected.append(self.accounts[row])
        return selected
    
    def start_processing(self):
        """开始处理"""
        selected = self.get_selected_accounts()
        
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要处理的账号")
            return
        
        # recovery模式必须有备用邮箱
        if self.mode == "recovery" and not self.recovery_emails:
            QMessageBox.warning(self, "提示", "请先创建 recovery_emails.txt 文件并添加备用邮箱")
            return
        
        # 获取模式文本
        mode_texts = {
            "2fa": "2FA密钥",
            "recovery": "辅助邮箱",
            "backup_codes": "备份验证码",
            "one_click": "安全信息（2FA+备份码+辅助邮箱）"
        }
        mode_text = mode_texts.get(self.mode, "安全信息")
        
        # 确认对话框
        confirm_msg = f"确定要批量处理 {len(selected)} 个账号的{mode_text}吗？"
        if self.mode == "one_click":
            confirm_msg += "\n\n将依次执行：\n1. 修改2FA密钥\n2. 获取备份验证码"
            if self.recovery_emails:
                confirm_msg += "\n3. 修改辅助邮箱"
        
        reply = QMessageBox.question(
            self, "确认",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log(f"\n{'='*50}")
        self.log(f"开始批量处理{mode_text}")
        self.log(f"选中账号: {len(selected)}")
        self.log(f"{'='*50}\n")
        
        # 创建工作线程
        self.worker = SecurityWorkerThread(self.mode, selected, self.recovery_emails)
        self.worker.log_signal.connect(self.log)
        self.worker.progress_signal.connect(self.update_account_status)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.request_code_signal.connect(self.on_request_verification_code)
        self.worker.start()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_refresh.setEnabled(False)
    
    def stop_processing(self):
        """停止处理"""
        if self.worker:
            self.worker.stop()
            self.log("⚠️ 正在停止...")
    
    def on_finished(self, result):
        """处理完成"""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_refresh.setEnabled(True)
        
        mode_texts = {
            "2fa": "2FA密钥修改",
            "recovery": "辅助邮箱修改",
            "backup_codes": "备份验证码获取",
            "one_click": "一键安全信息修改"
        }
        mode_text = mode_texts.get(self.mode, "安全信息处理")
        self.log(f"\n✅ {mode_text}任务完成！")
        QMessageBox.information(self, "完成", f"{mode_text}任务已完成")
    
    def on_request_verification_code(self, target_email):
        """请求验证码（弹窗）"""
        code, ok = QInputDialog.getText(
            self, 
            "需要验证码",
            f"请检查 {target_email} 的收件箱，\n输入收到的验证码:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and code:
            self.worker.set_verification_code(code.strip())
        else:
            self.worker.set_verification_code(None)
    
    def update_account_status(self, email, status, message):
        """更新表格状态"""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1) and self.table.item(row, 1).text() == email:
                self.table.setItem(row, 3, QTableWidgetItem(status))
                self.table.setItem(row, 4, QTableWidgetItem(message))
                break
    
    def mark_as_processed(self):
        """手动标记选中的账号为已处理"""
        selected = self.get_selected_accounts()
        
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要标记的账号")
            return
        
        reply = QMessageBox.question(
            self, "确认",
            f"确定将 {len(selected)} 个账号标记为已处理？\n(这不会实际修改账号，只是记录标记)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            import os
            from datetime import datetime
            
            base_path = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_path, "new_2fa_secrets.txt")
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(file_path, 'a', encoding='utf-8') as f:
                for account in selected:
                    email = account['email']
                    # 写入 MANUAL 标记表示手动添加
                    f.write(f"{timestamp} | {email} | MANUAL_MARKED\n")
                    self.processed_emails.add(email.lower())
            
            # 更新表格显示
            for row in range(self.table.rowCount()):
                email_item = self.table.item(row, 1)
                if email_item:
                    email = email_item.text()
                    if email.lower() in self.processed_emails:
                        status_item = QTableWidgetItem("✅ 已处理")
                        status_item.setForeground(Qt.GlobalColor.darkGreen)
                        self.table.setItem(row, 3, status_item)
                        # 取消勾选
                        checkbox_widget = self.table.cellWidget(row, 0)
                        if checkbox_widget:
                            checkbox = checkbox_widget.findChild(QCheckBox)
                            if checkbox:
                                checkbox.setChecked(False)
            
            self.log(f"✅ 已将 {len(selected)} 个账号标记为已处理")
            QMessageBox.information(self, "成功", f"已将 {len(selected)} 个账号标记为已处理")
            
        except Exception as e:
            self.log(f"❌ 标记失败: {e}")
            QMessageBox.critical(self, "错误", f"标记失败: {e}")
    
    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    app = QApplication(sys.argv)
    
    # 默认打开2FA修改窗口
    window = GoogleSecurityWindow(mode="2fa")
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
