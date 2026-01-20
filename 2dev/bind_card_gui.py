"""
绑卡订阅 GUI 界面
使用 auto_bind_card.py 的绑卡逻辑
"""
import sys
import os
import asyncio
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                              QPushButton, QLabel, QTextEdit, QTableWidget,
                              QTableWidgetItem, QHeaderView, QMessageBox,
                              QCheckBox, QLineEdit, QGroupBox, QFormLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# 设置 Windows 控制台为 UTF-8 编码以支持 emoji 字符
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'ignore')
    except:
        pass

from bit_api import openBrowser, closeBrowser
from create_window import get_browser_list
from auto_bind_card import auto_bind_card


class StreamToSignal:
    """重定向 stdout/stderr 到信号"""
    def __init__(self, signal):
        self.signal = signal
        self.buffer = ""

    def write(self, text):
        try:
            # 处理可能的编码问题
            if isinstance(text, bytes):
                text = text.decode('utf-8', 'replace')
            
            self.buffer += text
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                # 最后一个可能是不完整的行，保留在 buffer 中
                self.buffer = lines[-1]
                for line in lines[:-1]:
                    if line.strip():
                        self.signal.emit(safe_str(line.strip()))
        except Exception:
            pass
            
    def flush(self):
        if self.buffer.strip():
            self.signal.emit(safe_str(self.buffer.strip()))
            self.buffer = ""


def safe_str(text):
    """
    安全地转换文本，处理编码问题
    如果包含无法编码的字符，替换为安全的替代字符
    """
    try:
        # 尝试编码为 GBK，如果失败则替换特殊字符
        text.encode('gbk')
        return text
    except (UnicodeEncodeError, UnicodeDecodeError):
        # 替换常见的 emoji 为文字
        replacements = {
            '✅': '[成功]',
            '❌': '[失败]',
            '⚠️': '[警告]',
            '📊': '[统计]',
            '💳': '[卡片]',
            '🔑': '[密钥]',
        }
        for emoji, text_replacement in replacements.items():
            text = text.replace(emoji, text_replacement)
        return text


class BindCardWorkerThread(QThread):
    """绑卡工作线程"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str, str, str)  # browser_id, status, message
    finished_signal = pyqtSignal(dict)
    

    
    def __init__(self, accounts, cards, cards_per_account=1, keep_browser_on_error=False):
        super().__init__()
        self.accounts = accounts
        self.cards = cards
        self.cards_per_account = cards_per_account
        self.keep_browser_on_error = keep_browser_on_error
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
    def run(self):
        try:
            asyncio.run(self._process_all())
        except Exception as e:
            self.log_signal.emit(safe_str(f"❌ 工作线程错误: {e}"))
            import traceback
            traceback.print_exc()
        finally:
            self.finished_signal.emit({'success': True})
    
    async def _process_all(self):
        """处理所有账号"""
        total = len(self.accounts)
        success_count = 0
        fail_count = 0
        
        card_index = 0
        card_usage_count = 0
        
        for i, account in enumerate(self.accounts):
            if not self.is_running:
                self.log_signal.emit(safe_str("⚠️ 任务已停止"))
                break
            
            browser_id = account.get('browser_id', '')
            email = account.get('email', '')
            
            self.log_signal.emit(safe_str(f"\n{'='*50}"))
            self.log_signal.emit(safe_str(f"[{i+1}/{total}] 处理账号: {email}"))
            self.log_signal.emit(safe_str(f"{'='*50}"))
            
            # 检查是否需要切换到下一张卡
            if card_usage_count >= self.cards_per_account:
                card_index += 1
                card_usage_count = 0
                self.log_signal.emit(safe_str(f"💳 切换到下一张卡 (卡 #{card_index + 1})"))
            
            # 检查卡是否用完
            if card_index >= len(self.cards):
                self.log_signal.emit(safe_str("⚠️ 卡片已用完，停止处理"))
                break
            
            current_card = self.cards[card_index] if card_index < len(self.cards) else None
            
            if not current_card:
                msg = "没有可用的卡片"
                self.progress_signal.emit(browser_id, safe_str("❌ 失败"), msg)
                self.log_signal.emit(safe_str(f"[{i+1}] ❌ {email}: {msg}"))
                fail_count += 1
                continue
            
            try:
                # 打开浏览器
                result = openBrowser(browser_id)
                if not result.get('success'):
                    msg = "打开浏览器失败"
                    self.progress_signal.emit(browser_id, safe_str("❌ 失败"), msg)
                    self.log_signal.emit(safe_str(f"[{i+1}] ❌ {email}: {msg}"))
                    fail_count += 1
                    continue
                
                ws_endpoint = result['data']['ws']
                
                # 使用 Playwright 连接
                from playwright.async_api import async_playwright
                
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.connect_over_cdp(ws_endpoint)
                    context = browser.contexts[0]
                    page = context.pages[0] if context.pages else await context.new_page()
                    
                    # 执行绑卡 (传入账号信息以支持自动登录)
                    success, message = await auto_bind_card(
                        page,
                        card_info=current_card,
                        account_info=account
                    )
                    
                    if success:
                        self.progress_signal.emit(browser_id, safe_str("✅ 成功"), message)
                        self.log_signal.emit(safe_str(f"[{i+1}] ✅ {email}: {message}"))
                        success_count += 1
                        card_usage_count += 1
                    else:
                        self.progress_signal.emit(browser_id, safe_str("❌ 失败"), message)
                        self.log_signal.emit(safe_str(f"[{i+1}] ❌ {email}: {message}"))
                        fail_count += 1
                
                # 关闭浏览器
                if not success and self.keep_browser_on_error:
                    self.log_signal.emit(safe_str(f"⚠️ 发生错误，保留浏览器 {browser_id} 以便调试"))
                else:
                    closeBrowser(browser_id)
                
            except Exception as e:
                error_msg = f"处理出错: {e}"
                self.progress_signal.emit(browser_id, safe_str("❌ 错误"), error_msg)
                self.log_signal.emit(safe_str(f"[{i+1}] ❌ {email}: {error_msg}"))
                fail_count += 1
            
            # 延迟
            if i < total - 1 and self.is_running:
                await asyncio.sleep(3)
        
        self.log_signal.emit(safe_str(f"\n{'='*50}"))
        self.log_signal.emit(safe_str(f"📊 处理完成: 成功 {success_count}, 失败 {fail_count}"))
        self.log_signal.emit(safe_str(f"{'='*50}"))


class BindCardWindow(QWidget):
    """绑卡订阅窗口"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.accounts = []
        self.cards = []
        self.initUI()
        self.load_accounts()
        self.load_cards()
    
    def initUI(self):
        self.setWindowTitle("一键绑卡订阅")
        self.setGeometry(100, 100, 1000, 750)
        
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("💳 一键绑卡订阅")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 卡片和账号信息
        info_layout = QHBoxLayout()
        self.card_count_label = QLabel("卡片: 0")
        info_layout.addWidget(self.card_count_label)
        self.account_count_label = QLabel("账号: 0")
        info_layout.addWidget(self.account_count_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # 设置区域
        settings_group = QGroupBox("绑卡设置")
        settings_layout = QFormLayout()
        
        # 一卡几绑
        self.cards_per_account_input = QLineEdit("1")
        settings_layout.addRow("一卡几绑:", self.cards_per_account_input)
        

        
        # 失败保持浏览器开启
        self.keep_browser_checkbox = QCheckBox("失败时保持浏览器开启")
        self.keep_browser_checkbox.setChecked(True)
        settings_layout.addRow("", self.keep_browser_checkbox)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # 全选复选框
        select_layout = QHBoxLayout()
        self.select_all_checkbox = QCheckBox("全选/取消全选")
        self.select_all_checkbox.stateChanged.connect(self.toggle_select_all)
        select_layout.addWidget(self.select_all_checkbox)
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        # 账号列表
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选择", "邮箱", "浏览器ID", "状态", "消息"])
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
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton("刷新列表")
        self.btn_refresh.clicked.connect(self.refresh_all)
        button_layout.addWidget(self.btn_refresh)
        
        self.btn_start = QPushButton("开始绑卡")
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        button_layout.addWidget(self.btn_start)
        
        # 打开调试日志按钮
        self.btn_debug = QPushButton("显示所有日志")
        self.btn_debug.setCheckable(True)
        button_layout.addWidget(self.btn_debug)

        
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_processing)
        button_layout.addWidget(self.btn_stop)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_cards(self):
        """加载 cards.txt"""
        base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        cards_path = os.path.join(base_path, "cards.txt")
        
        self.cards = []
        
        if not os.path.exists(cards_path):
            self.card_count_label.setText("卡片: 0")
            return
        
        try:
            with open(cards_path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
            
            for line in lines:
                if line.startswith('分隔符='):
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    card = {
                        'number': parts[0].strip(),
                        'exp_month': parts[1].strip(),
                        'exp_year': parts[2].strip(),
                        'cvv': parts[3].strip()
                    }
                    self.cards.append(card)
            
            self.card_count_label.setText(f"卡片: {len(self.cards)}")
            self.log(f"✅ 加载了 {len(self.cards)} 张卡片")
            
        except Exception as e:
            self.log(f"❌ 加载卡片失败: {e}")
    
    def load_accounts(self):
        """加载所有账号"""
        try:
            browsers = get_browser_list(page=0, pageSize=1000)
            
            self.table.setRowCount(0)
            self.accounts = []
            
            for browser in browsers:
                remark = browser.get('remark', '')
                # 支持两种分隔符: '----' 和 '---'
                separator = '----' if '----' in remark else '---'
                if separator in remark:
                    parts = remark.split(separator)
                    if parts and '@' in parts[0]:
                        account = {
                            'email': parts[0].strip(),
                            'password': parts[1].strip() if len(parts) > 1 else '',
                            'backup': parts[2].strip() if len(parts) > 2 else '',
                            'secret': parts[3].strip() if len(parts) > 3 else '',
                            'browser_id': browser.get('id', '')
                        }
                        self.accounts.append(account)
                        
                        # 添加到表格
                        row_idx = self.table.rowCount()
                        self.table.insertRow(row_idx)
                        
                        # 复选框
                        checkbox = QCheckBox()
                        checkbox.setChecked(True)
                        checkbox_widget = QWidget()
                        checkbox_layout = QHBoxLayout(checkbox_widget)
                        checkbox_layout.addWidget(checkbox)
                        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        checkbox_layout.setContentsMargins(0, 0, 0, 0)
                        self.table.setCellWidget(row_idx, 0, checkbox_widget)
                        
                        self.table.setItem(row_idx, 1, QTableWidgetItem(account['email']))
                        self.table.setItem(row_idx, 2, QTableWidgetItem(account['browser_id']))
                        self.table.setItem(row_idx, 3, QTableWidgetItem("待处理"))
                        self.table.setItem(row_idx, 4, QTableWidgetItem(""))
            
            self.account_count_label.setText(f"账号: {len(self.accounts)}")
            self.log(f"✅ 加载了 {len(self.accounts)} 个账号")
            
        except Exception as e:
            self.log(f"❌ 加载账号失败: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh_all(self):
        """刷新"""
        self.load_accounts()
        self.load_cards()
    
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
        selected_accounts = self.get_selected_accounts()
        
        if not selected_accounts:
            QMessageBox.warning(self, "提示", "请先勾选要处理的账号")
            return
        
        if not self.cards:
            QMessageBox.warning(self, "提示", "请先添加卡片到 cards.txt")
            return
        
        try:
            cards_per_account = int(self.cards_per_account_input.text())
        except:
            QMessageBox.warning(self, "提示", "请输入有效的一卡几绑数量")
            return
        
        self.log(f"\n{'='*50}")
        self.log(f"开始绑卡订阅")
        self.log(f"选中账号: {len(selected_accounts)}")
        self.log(f"卡片数量: {len(self.cards)}")
        self.log(f"一卡几绑: {cards_per_account}")
        self.log(f"{'='*50}\n")
        
        # 创建并启动工作线程
        self.worker = BindCardWorkerThread(
            selected_accounts,
            self.cards,
            cards_per_account,
            self.keep_browser_checkbox.isChecked()
        )
        self.worker.progress_signal.connect(self.update_account_status)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        
        # 如果开启了调试模式，重定向 stdout
        if self.btn_debug.isChecked():
            sys.stdout = StreamToSignal(self.worker.log_signal)
            sys.stderr = StreamToSignal(self.worker.log_signal)
            self.log("[DEBUG] 已开启详细日志模式 (stdout redirection enabled)")
        
        self.worker.start()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_refresh.setEnabled(False)
    
    def stop_processing(self):
        """停止处理"""
        if self.worker:
            self.worker.stop()
            self.log("⚠️ 正在停止...")
            
        # 恢复 stdout
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    
    def on_finished(self):
        """处理完成"""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_refresh.setEnabled(True)
        # 恢复 stdout
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
        self.log("\n✅ 绑卡任务完成！")
        QMessageBox.information(self, "完成", "绑卡任务已完成")
    
    def update_account_status(self, browser_id, status, message):
        """更新表格状态"""
        for row in range(self.table.rowCount()):
            if self.table.item(row, 2) and self.table.item(row, 2).text() == browser_id:
                self.table.setItem(row, 3, QTableWidgetItem(status))
                self.table.setItem(row, 4, QTableWidgetItem(message))
                break
    
    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    app = QApplication(sys.argv)
    window = BindCardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
