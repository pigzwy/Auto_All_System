"""
IMAP验证码读取调试脚本
用于诊断为什么直接用163邮箱作为辅助邮箱时验证码读取失败
"""
import asyncio
import time
from email_verifier import EmailVerifier, get_google_verification_code_from_163


def test_basic_connection():
    """测试1: 基本IMAP连接"""
    print("=" * 60)
    print("测试1: IMAP基本连接测试")
    print("=" * 60)
    
    email = "chujian123qwe@163.com"
    password = "NGtB4HF8KPtD9MKC"
    
    verifier = EmailVerifier('imap.163.com', email, password, log_callback=print)
    
    if verifier.connect():
        print("✅ IMAP连接成功")
        verifier.disconnect()
        return True
    else:
        print("❌ IMAP连接失败")
        return False


def test_read_latest_emails():
    """测试2: 读取最新邮件（查看是否有Google邮件）"""
    print("\n" + "=" * 60)
    print("测试2: 读取收件箱最新5封邮件")
    print("=" * 60)
    
    import imaplib
    import email
    from email.header import decode_header
    
    try:
        imap = imaplib.IMAP4_SSL('imap.163.com')
        imap.login("chujian123qwe@163.com", "NGtB4HF8KPtD9MKC")
        print("✅ 登录成功")
        
        imap.select('INBOX')
        
        # 获取所有邮件（最新的5封）
        status, messages = imap.search(None, 'ALL')
        email_ids = messages[0].split()
        
        if not email_ids:
            print("📭 收件箱为空")
            imap.logout()
            return
        
        print(f"📬 收件箱共有 {len(email_ids)} 封邮件")
        print("\n查看最新5封邮件：\n")
        
        # 获取最新5封
        for email_id in reversed(email_ids[-5:]):
            status, msg_data = imap.fetch(email_id, '(RFC822)')
            
            if status != 'OK':
                continue
            
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # 获取主题
            subject_header = email_message.get('Subject', '')
            subject = ''
            for part, encoding in decode_header(subject_header):
                if isinstance(part, bytes):
                    try:
                        subject += part.decode(encoding or 'utf-8')
                    except:
                        subject += part.decode('utf-8', errors='ignore')
                else:
                    subject += str(part)
            
            # 获取发件人
            sender = email_message.get('From', '')
            
            # 获取日期
            date = email_message.get('Date', '')
            
            print(f"📧 邮件 ID: {email_id.decode()}")
            print(f"   发件人: {sender}")
            print(f"   主题: {subject}")
            print(f"   日期: {date}")
            
            # 检查是否是Google邮件
            if 'google' in sender.lower():
                print(f"   ⭐ 这是Google邮件！")
                
                # 尝试提取正文
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == 'text/plain':
                            try:
                                payload = part.get_payload(decode=True)
                                body = payload.decode('utf-8', errors='ignore')
                                break
                            except:
                                pass
                else:
                    try:
                        payload = email_message.get_payload(decode=True)
                        body = payload.decode('utf-8', errors='ignore')
                    except:
                        pass
                
                if body:
                    print(f"   正文预览: {body[:200]}...")
                    
                    # 尝试提取验证码
                    import re
                    patterns = [
                        r'verification code[:\s]+(\d{6})',
                        r'code[:\s]+(\d{6})',
                        r'(\d{6})[:\s]+is your',
                        r'验证码[：:\s]+(\d{6})',
                        r'\b(\d{6})\b',
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, body, re.IGNORECASE)
                        if match:
                            code = match.group(1)
                            if len(code) == 6 and code.isdigit():
                                print(f"   ✅ 找到验证码: {code}")
                                break
            
            print()
        
        imap.logout()
        
    except Exception as e:
        print(f"❌ 读取邮件失败: {e}")
        import traceback
        traceback.print_exc()


def test_wait_for_verification_code():
    """测试3: 模拟等待验证码（你需要先手动触发Google发送验证码）"""
    print("\n" + "=" * 60)
    print("测试3: 等待Google验证码")
    print("=" * 60)
    print("⚠️ 请先在Google账号中触发发送验证码到 chujian123qwe@163.com")
    print("   然后按回车开始监听...")
    input()
    
    print("\n🔍 开始监听验证码邮件（等待120秒）...\n")
    
    code = get_google_verification_code_from_163(
        email_address="chujian123qwe@163.com",
        auth_code="NGtB4HF8KPtD9MKC",
        recovery_email="chujian123qwe@163.com",  # 这里填实际的目标邮箱
        timeout=120,
        log_callback=print
    )
    
    if code:
        print(f"\n✅ 成功获取验证码: {code}")
    else:
        print(f"\n❌ 未能获取验证码")


def main():
    print("\n[DEBUG] IMAP verification code reading debug script\n")
    
    # 测试1: 连接
    if not test_basic_connection():
        print("\n❌ IMAP连接失败，请检查账号密码")
        return
    
    # 测试2: 读取最新邮件
    test_read_latest_emails()
    
    # 测试3: 等待验证码（可选）
    print("\n是否要测试等待验证码？(y/n): ", end='')
    choice = input().strip().lower()
    
    if choice == 'y':
        test_wait_for_verification_code()
    
    print("\n✅ 调试完成！")


if __name__ == "__main__":
    main()
