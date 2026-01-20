"""查找所有浏览器信息"""
from create_window import get_browser_list

browsers = get_browser_list(page=0, pageSize=50)
print(f"找到 {len(browsers)} 个浏览器配置")
print()
for b in browsers[:10]:
    user_name = b.get('userName', '')
    remark = b.get('remark', '')[:80] if b.get('remark') else 'N/A'
    print(f"ID: {b.get('id')}")
    print(f"Name: {user_name}")
    print(f"Remark: {remark}")
    print("---")
