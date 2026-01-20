"""
邮件验证码自动读取模块
支持通过IMAP协议从163邮箱自动获取Google发送的验证码
"""
import imaplib
import email
from email.header import decode_header
import re
import time
from datetime import datetime, timedelta


class EmailVerifier:
    """邮件验证码读取器"""
    
    def __init__(self, imap_server: str, email_address: str, password: str, log_callback=None):
        """
        初始化邮件验证码读取器
        
        Args:
            imap_server: IMAP服务器地址 (例如 'imap.163.com')
            email_address: 邮箱地址
            password: 邮箱密码或授权码
            log_callback: 日志回调函数
        """
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
        self.log_callback = log_callback
        self.imap = None
    
    def log(self, msg):
        """输出日志"""
        if self.log_callback:
            self.log_callback(msg)
        try:
            print(msg)
        except:
            pass
    
    def connect(self):
        """连接到IMAP服务器"""
        try:
            self.log(f"[INFO] Connecting to {self.imap_server}...")
            self.imap = imaplib.IMAP4_SSL(self.imap_server)
            self.imap.login(self.email_address, self.password)
            self.log("[OK] IMAP connection successful")
            return True
        except Exception as e:
            self.log(f"[ERROR] IMAP connection failed: {e}")
            return False
    
    def disconnect(self):
        """断开IMAP连接"""
        try:
            if self.imap:
                self.imap.logout()
                self.log("[INFO] IMAP connection closed")
        except:
            pass
    
    def get_verification_code(self, recipient_email: str, timeout: int = 120, check_interval: int = 5):
        """
        从邮箱中获取Google发送的验证码
        
        Args:
            recipient_email: 接收验证码的邮箱地址（用于过滤邮件主题）
            timeout: 最大等待时间（秒）
            check_interval: 检查间隔（秒）
        
        Returns:
            str: 验证码，如果未找到返回None
        """
        self.log(f"🔍 开始查找验证码邮件 (目标: {recipient_email})...")
        
        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < timeout:
            attempts += 1
            self.log(f"   尝试 {attempts} - 检查收件箱...")
            
            try:
                # 选择收件箱
                self.imap.select('INBOX')
                
                # 搜索最近5分钟内的未读邮件
                # 使用UNSEEN标志查找未读邮件
                search_criteria = '(UNSEEN)'
                
                # 也可以添加发件人过滤
                # search_criteria = '(UNSEEN FROM "no-reply@accounts.google.com")'
                
                status, messages = self.imap.search(None, search_criteria)
                
                if status != 'OK':
                    self.log("   未找到新邮件")
                    time.sleep(check_interval)
                    continue
                
                email_ids = messages[0].split()
                
                if not email_ids:
                    self.log("   收件箱中暂无未读邮件")
                    time.sleep(check_interval)
                    continue
                
                self.log(f"   找到 {len(email_ids)} 封未读邮件，正在检查...")
                
                # 从最新的邮件开始检查
                for email_id in reversed(email_ids):
                    try:
                        # 获取邮件
                        status, msg_data = self.imap.fetch(email_id, '(RFC822)')
                        
                        if status != 'OK':
                            continue
                        
                        # 解析邮件
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        
                        # 获取邮件主题
                        subject = self._decode_subject(email_message.get('Subject', ''))
                        sender = email_message.get('From', '')
                        
                        self.log(f"   检查邮件: {subject[:50]}...")
                        
                        # 检查是否是Google验证码邮件
                        # Google发送的验证码邮件通常包含 "verification code", "verify", 等关键词
                        if not self._is_google_verification_email(subject, sender):
                            continue
                        
                        self.log(f"✅ 找到Google验证码邮件: {subject}")
                        
                        # 提取邮件正文
                        body = self._get_email_body(email_message)
                        
                        # 从邮件正文提取验证码
                        code = self._extract_verification_code(body)
                        
                        if code:
                            self.log(f"✅ 成功提取验证码: {code}")
                            # 标记为已读（可选）
                            # self.imap.store(email_id, '+FLAGS', '\\Seen')
                            return code
                        
                    except Exception as e:
                        self.log(f"   解析邮件时出错: {e}")
                        continue
                
                self.log(f"   未找到验证码，{check_interval}秒后重试...")
                time.sleep(check_interval)
                
            except Exception as e:
                self.log(f"⚠️ 检查邮件时出错: {e}")
                time.sleep(check_interval)
        
        self.log(f"❌ 超时：在 {timeout} 秒内未找到验证码")
        return None
    
    def _decode_subject(self, subject):
        """解码邮件主题"""
        if not subject:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(subject):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8'))
                except:
                    decoded_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(str(part))
        
        return ''.join(decoded_parts)
    
    def _is_google_verification_email(self, subject: str, sender: str):
        """检查是否是Google验证码邮件"""
        # 检查发件人
        google_senders = [
            'google',
            'accounts.google',
            'no-reply@accounts.google.com',
            'noreply@google.com'
        ]
        
        sender_lower = sender.lower()
        is_google_sender = any(s in sender_lower for s in google_senders)
        
        # 检查主题关键词
        subject_lower = subject.lower()
        verification_keywords = [
            'verification code',
            'verify',
            'security code',
            '验证码',
            '验证',
            '安全码',
            'email address',
            '邮箱地址'
        ]
        
        has_verification_keyword = any(kw in subject_lower for kw in verification_keywords)
        
        return is_google_sender and has_verification_keyword
    
    def _get_email_body(self, email_message):
        """提取邮件正文"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                disposition = str(part.get('Content-Disposition', ''))
                
                # 跳过附件
                if 'attachment' in disposition:
                    continue
                
                # 获取文本内容
                if content_type in ['text/plain', 'text/html']:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='ignore')
                    except:
                        pass
        else:
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
            except:
                pass
        
        return body
    
    def _extract_verification_code(self, body: str):
        """从邮件正文提取验证码"""
        # Google验证码通常是6位数字
        # 常见模式：
        # - "Your verification code is: 123456"
        # - "verification code: 123456"
        # - "123456 is your verification code"
        # - 直接显示的6位数字
        
        patterns = [
            r'verification code[:\s]+(\d{6})',  # verification code: 123456
            r'code[:\s]+(\d{6})',                # code: 123456
            r'(\d{6})[:\s]+is your',            # 123456 is your
            r'验证码[：:\s]+(\d{6})',              # 验证码：123456
            r'[：:\s](\d{6})[：:\s]',            # 通用6位数字
            r'\b(\d{6})\b',                      # 独立的6位数字
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                code = match.group(1)
                # 验证是否真的是6位数字
                if len(code) == 6 and code.isdigit():
                    return code
        
        return None


# 163邮箱配置
IMAP_163_SERVER = 'imap.163.com'
IMAP_163_PORT = 993


def get_google_verification_code_from_163(email_address: str, auth_code: str, 
                                          recovery_email: str, 
                                          timeout: int = 120,
                                          log_callback=None):
    """
    从163邮箱获取Google验证码的便捷函数
    
    Args:
        email_address: 163邮箱地址
        auth_code: 163邮箱授权码
        recovery_email: Google辅助邮箱地址（用于识别）
        timeout: 超时时间（秒）
        log_callback: 日志回调函数
    
    Returns:
        str: 验证码，如果失败返回None
    """
    verifier = EmailVerifier(IMAP_163_SERVER, email_address, auth_code, log_callback)
    
    try:
        if not verifier.connect():
            return None
        
        code = verifier.get_verification_code(recovery_email, timeout=timeout)
        return code
    
    finally:
        verifier.disconnect()


if __name__ == "__main__":
    # 测试代码
    print("测试IMAP邮件验证码读取...")
    
    # 使用用户提供的配置
    email = "chujian123qwe@163.com"
    auth = "NGtB4HF8KPtD9MKC"
    recovery = "test@xiaochujian.asia"
    
    code = get_google_verification_code_from_163(email, auth, recovery, timeout=60)
    
    if code:
        print(f"成功获取验证码: {code}")
    else:
        print("未能获取验证码")
