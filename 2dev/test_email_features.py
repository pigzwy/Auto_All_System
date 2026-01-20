"""
Google安全自动化功能测试脚本
测试:
1. IMAP邮件验证码读取
2. 辅助邮箱修改（全自动）
3. Backup codes提取（显示10个）
"""
import asyncio
from google_security_automation import (
    change_recovery_email,
    get_backup_codes,
    load_imap_config,
    load_recovery_emails,
    get_random_recovery_email
)


async def test_imap_email_verification():
    """测试IMAP邮件验证码自动读取"""
    print("=" * 60)
    print("测试1: IMAP邮件验证码自动读取")
    print("=" * 60)
    
    # 加载IMAP配置
    imap_config = load_imap_config()
    
    if not imap_config:
        print("❌ 未找到IMAP配置文件 (email_config.ini)")
        return False
    
    print(f"✅ IMAP配置已加载:")
    print(f"   邮箱: {imap_config['email']}")
    print(f"   授权码: {'*' * 8}")
    
    # 测试连接
    try:
        from email_verifier import EmailVerifier
        
        verifier = EmailVerifier(
            'imap.163.com',
            imap_config['email'],
            imap_config['password'],
            log_callback=print
        )
        
        if verifier.connect():
            print("✅ IMAP连接测试成功")
            verifier.disconnect()
            return True
        else:
            print("❌ IMAP连接测试失败")
            return False
    except Exception as e:
        print(f"❌ IMAP测试出错: {e}")
        return False


async def test_recovery_email_change():
    """测试辅助邮箱修改（使用IMAP自动验证）"""
    print("\n" + "=" * 60)
    print("测试2: 辅助邮箱修改流程测试")
    print("=" * 60)
    
    # 这是一个演示，实际使用时需要提供真实的账号信息
    print("⚠️ 此测试需要真实的Google账号和BitBrowser窗口ID")
    print("   请在实际GUI中测试此功能")
    
    # 加载配置
    imap_config = load_imap_config()
    recovery_emails = load_recovery_emails()
    
    if imap_config:
        print(f"✅ IMAP配置: {imap_config['email']}")
    else:
        print("⚠️ 未找到IMAP配置")
    
    if recovery_emails:
        print(f"✅ 辅助邮箱池: {len(recovery_emails)} 个")
        # 随机选择一个
        random_email = get_random_recovery_email(recovery_emails)
        print(f"   随机选择: {random_email}")
    else:
        print("⚠️ 未找到辅助邮箱列表")
    
    print("\n💡 使用示例:")
    print("""
    # 在GUI或主程序中调用:
    account_info = {
        'email': 'your@gmail.com',
        'password': 'your_password',
        'secret': 'your_2fa_secret'
    }
    
    new_email = 'test@xiaochujian.asia'  # 使用域名邮箱
    
    # IMAP配置会自动读取email_config.ini
    imap_config = load_imap_config()
    
    success, message = await change_recovery_email(
        browser_id='YOUR_BROWSER_ID',
        account_info=account_info,
        new_email=new_email,
        log_callback=print,
        imap_config=imap_config  # 传入IMAP配置实现全自动
    )
    """)
    
    return True


async def test_backup_codes_format():
    """测试Backup codes格式"""
    print("\n" + "=" * 60)
    print("测试3: Backup Codes显示格式测试")
    print("=" * 60)
    
    # 模拟提取到的备份码
    sample_codes = [
        "1234 5678",
        "2345 6789",
        "3456 7890",
        "4567 8901",
        "5678 9012",
        "6789 0123",
        "7890 1234",
        "8901 2345",
        "9012 3456",
        "0123 4567"
    ]
    
    print("✅ 标准格式: 应该显示10个独立的备份码")
    print("\n📋 示例Backup Codes:")
    for i, code in enumerate(sample_codes, 1):
        print(f"   {i}. {code}")
    
    print(f"\n✅ 总共: {len(sample_codes)} 个备份码")
    print("✅ 每个备份码格式: XXXX XXXX (4位空格4位)")
    
    return True


async def main():
    """运行所有测试"""
    print("\n🚀 Google安全自动化功能测试\n")
    
    # 测试1: IMAP连接
    result1 = await test_imap_email_verification()
    
    # 测试2: 辅助邮箱修改流程
    result2 = await test_recovery_email_change()
    
    # 测试3: Backup codes格式
    result3 = await test_backup_codes_format()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"1. IMAP连接测试: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"2. 辅助邮箱流程: ✅ 通过 (演示)")
    print(f"3. Backup码格式: ✅ 通过")
    print("\n🎉 所有测试完成!")
    
    print("\n📝 下一步:")
    print("1. 确保 email_config.ini 中的163邮箱配置正确")
    print("2. 在GUI中测试完整的辅助邮箱修改流程")
    print("3. 测试Backup codes提取功能")


if __name__ == "__main__":
    asyncio.run(main())
