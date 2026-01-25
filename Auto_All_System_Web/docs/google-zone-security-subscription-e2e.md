# Google 专区 Security / Subscription 端到端验证（Dev）

目标
- 确认 Google 专区 Security/Subscription 模块不再使用前端模拟轮询。
- 相关动作走后端 Celery + GeekezBrowser(Playwright CDP) 真自动化。
- 任务不会无限卡在 PROGRESS（有硬超时；最终能到 SUCCESS/FAILURE）。

前置条件
- Docker dev 环境已启动
- GeekezBrowser 已在宿主机运行，且 API 在容器内可通过 `http://host.docker.internal:19527` 访问

启动服务
```bash
cd Auto_All_System_Web
docker compose -f docker-compose.dev.yml up -d
```

验证服务状态
```bash
docker compose -f docker-compose.dev.yml ps
```

获取登录 token
```bash
python - <<"PY"
import requests
BASE='http://localhost:8000'
r=requests.post(BASE+'/api/v1/auth/login/', json={'username':'smoke','password':'smoke123'})
print(r.status_code)
print(r.json())
PY
```

记下 `data.access_token`，后续请求都带：
```text
Authorization: Bearer <access_token>
```

查询账号列表（取一个 account_id）
```bash
python - <<"PY"
import requests
BASE='http://localhost:8000'
token=requests.post(BASE+'/api/v1/auth/login/', json={'username':'smoke','password':'smoke123'}).json()['data']['access_token']
h={'Authorization':f'Bearer {token}'}
r=requests.get(BASE+'/api/v1/plugins/google-business/accounts/?page_size=5', headers=h)
print(r.status_code)
print(r.text)
PY
```

Security - 获取备份码（Celery task_id）
```bash
POST /api/v1/plugins/google-business/security/get_backup_codes/
{
  "account_ids": [<id>],
  "browser_type": "geekez"
}
```

Security - 修改 2FA
```bash
POST /api/v1/plugins/google-business/security/change_2fa/
{
  "account_ids": [<id>],
  "browser_type": "geekez"
}
```

Security - 修改辅助邮箱
```bash
POST /api/v1/plugins/google-business/security/change_recovery_email/
{
  "account_ids": [<id>],
  "new_email": "backup2@example.com",
  "browser_type": "geekez"
}
```

Security - 一键安全设置
```bash
POST /api/v1/plugins/google-business/security/one_click_update/
{
  "account_ids": [<id>],
  "browser_type": "geekez"
}
```

Subscription - 验证订阅状态
```bash
POST /api/v1/plugins/google-business/subscription/verify_status/
{
  "account_ids": [<id>],
  "take_screenshot": true,
  "browser_type": "geekez"
}
```

Subscription - 点击订阅
```bash
POST /api/v1/plugins/google-business/subscription/click_subscribe/
{
  "account_ids": [<id>],
  "browser_type": "geekez"
}
```

轮询 Celery task 状态（前端也使用这个接口）
```bash
GET /api/v1/plugins/google-business/celery-tasks/<task_id>/
```

返回结构示例
```json
{
  "task_id": "...",
  "state": "SUCCESS",
  "result": {
    "success": true,
    "results": [
      {
        "email": "xxx@gmail.com",
        "success": false,
        "message": "登录失败: ..."
      }
    ],
    "total": 1,
    "succeeded": 0
  }
}
```

取消 Celery task（可选）
```bash
POST /api/v1/plugins/google-business/celery-tasks/<task_id>/cancel/
```

常见问题

1) 429 请求限速
- 症状：接口返回 `429 Too Many Requests`。
- 解决：开发环境已将 DRF throttle 从 day 级别改为 hour 级别（保证轮询可用）。如仍触发，减少轮询频率。

2) 任务卡在 PROGRESS
- 现在每个账号动作都有硬超时（避免无限等待）。
- 若仍看到 PROGRESS 长期不结束：检查 celery worker 是否加载最新代码（重启 celery）。

3) 登录超时
- 当前 smoke 示例账号可能无法完成真实 Google 登录（会出现 `Login timeout`）。
- 但验证重点是：任务能真实调起浏览器、能按预期失败返回、能结束不挂死。
