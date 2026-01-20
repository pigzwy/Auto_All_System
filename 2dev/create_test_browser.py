# -*- coding: utf-8 -*-
"""创建测试账号的浏览器窗口"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from create_window import create_browser_window, get_browser_list

# 测试账号信息: JennyBachir331@gmail.com----jfrlbr3l1m----JennyBachir33161821@myfreshmail.online----lqkrowcrwxiwveffgntqw6nkswjcr7ar
full_line = 'JennyBachir331@gmail.com----jfrlbr3l1m----JennyBachir33161821@myfreshmail.online----lqkrowcrwxiwveffgntqw6nkswjcr7ar'
account = {
    'email': 'JennyBachir331@gmail.com',
    'password': 'jfrlbr3l1m',
    'backup': 'JennyBachir33161821@myfreshmail.online',
    'secret': 'lqkrowcrwxiwveffgntqw6nkswjcr7ar',
    'name': 'JennyBachir331',
    'full_line': full_line
}

# 用已有的浏览器作为模板
browsers = get_browser_list(page=0, pageSize=100)
reference_id = None
for b in browsers:
    if b.get('id'):
        reference_id = b.get('id')
        print(f"Using reference browser: {b.get('userName')} ({reference_id})")
        break

if reference_id:
    browser_id, error = create_browser_window(
        account=account,
        reference_browser_id=reference_id,
        name_prefix='Test'
    )
    
    if browser_id:
        print(f"Successfully created browser window: {browser_id}")
    else:
        print(f"Failed to create browser: {error}")
else:
    print("No reference browser found!")
