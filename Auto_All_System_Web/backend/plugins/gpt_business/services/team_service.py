# Team 服务模块 - 处理 ChatGPT Team 邀请相关功能
# 从 oai-team-auto-provisioner/team_service.py 移植

import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 30


def create_session_with_retry() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


http_session = create_session_with_retry()


def fetch_account_id(auth_token: str) -> tuple[str, str]:
    """通过 API 获取 account_id
    
    Returns:
        tuple: (account_id, plan_type)
    """
    if not auth_token:
        return "", ""

    if not auth_token.startswith("Bearer "):
        auth_token = f"Bearer {auth_token}"

    headers = {
        "accept": "*/*",
        "authorization": auth_token,
        "content-type": "application/json",
        "user-agent": USER_AGENT,
    }

    try:
        response = http_session.get(
            "https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            accounts = data.get("accounts", {})

            if accounts:
                for acc_id, acc_info in accounts.items():
                    if acc_id == "default":
                        continue
                    account_data = acc_info.get("account", {})
                    plan_type = account_data.get("plan_type", "")
                    if "team" in plan_type.lower():
                        logger.info(f"获取到 Team account_id: {acc_id[:8]}...")
                        return acc_id, plan_type

                for acc_id in accounts.keys():
                    if acc_id != "default":
                        logger.info(f"获取到 account_id: {acc_id[:8]}...")
                        return acc_id, ""
        else:
            logger.warning(f"获取 account_id 失败: HTTP {response.status_code}")

    except Exception as e:
        logger.warning(f"获取 account_id 失败: {e}")

    return "", ""


def get_team_stats(auth_token: str, account_id: str) -> dict:
    """获取 Team 的统计信息 (席位使用情况)
    
    Returns:
        dict: {"seats_in_use": int, "seats_entitled": int, "pending_invites": int, "plan_type": str}
    """
    if not auth_token.startswith("Bearer "):
        auth_token = f"Bearer {auth_token}"

    headers = {
        "accept": "*/*",
        "authorization": auth_token,
        "content-type": "application/json",
        "user-agent": USER_AGENT,
        "chatgpt-account-id": account_id,
    }

    try:
        response = http_session.get(
            f"https://chatgpt.com/backend-api/subscriptions?account_id={account_id}",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "seats_in_use": data.get("seats_in_use", 0),
                "seats_entitled": data.get("seats_entitled", 0),
                "pending_invites": data.get("pending_invites", 0),
                "plan_type": data.get("plan_type", ""),
            }
        else:
            logger.warning(f"获取 Team 统计失败: HTTP {response.status_code}")

    except Exception as e:
        logger.warning(f"获取 Team 统计异常: {e}")

    return {}


def check_available_seats(auth_token: str, account_id: str) -> int:
    """检查 Team 可用席位数"""
    stats = get_team_stats(auth_token, account_id)

    if not stats:
        return 0

    seats_in_use = stats.get("seats_in_use", 0)
    seats_entitled = stats.get("seats_entitled", 5)
    pending_invites = stats.get("pending_invites", 0)

    available = seats_entitled - seats_in_use - pending_invites
    return max(0, available)


def batch_invite_to_team(emails: list, auth_token: str, account_id: str) -> dict:
    """批量邀请多个邮箱到 Team
    
    Returns:
        dict: {"success": [...], "failed": [...]}
    """
    if not auth_token.startswith("Bearer "):
        auth_token = f"Bearer {auth_token}"

    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": auth_token,
        "content-type": "application/json",
        "origin": "https://chatgpt.com",
        "referer": "https://chatgpt.com/",
        "user-agent": USER_AGENT,
        "chatgpt-account-id": account_id,
    }

    payload = {
        "email_addresses": emails,
        "role": "standard-user",
        "resend_emails": True
    }
    
    invite_url = f"https://chatgpt.com/backend-api/accounts/{account_id}/invites"

    result = {"success": [], "failed": []}

    try:
        logger.info(f"批量邀请 {len(emails)} 个邮箱到 Team {account_id[:8]}...")
        response = http_session.post(invite_url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)

        if response.status_code == 200:
            resp_data = response.json()

            if resp_data.get("account_invites"):
                for invite in resp_data["account_invites"]:
                    invited_email = invite.get("email_address", "")
                    if invited_email:
                        result["success"].append(invited_email)
                        logger.info(f"邀请成功: {invited_email}")

            if resp_data.get("errored_emails"):
                for err in resp_data["errored_emails"]:
                    err_email = err.get("email", "")
                    err_msg = err.get("error", "Unknown error")
                    if err_email:
                        result["failed"].append({"email": err_email, "error": err_msg})
                        logger.error(f"邀请失败: {err_email} - {err_msg}")

            if not resp_data.get("account_invites") and not resp_data.get("errored_emails"):
                result["success"] = emails
        else:
            logger.error(f"批量邀请失败: HTTP {response.status_code}")
            result["failed"] = [{"email": e, "error": f"HTTP {response.status_code}"} for e in emails]

    except Exception as e:
        logger.error(f"批量邀请异常: {e}")
        result["failed"] = [{"email": e, "error": str(e)} for e in emails]

    logger.info(f"邀请结果: 成功 {len(result['success'])}, 失败 {len(result['failed'])}")
    return result


def invite_single_email(email: str, auth_token: str, account_id: str) -> tuple[bool, str]:
    """邀请单个邮箱到 Team
    
    Returns:
        tuple: (success, message)
    """
    result = batch_invite_to_team([email], auth_token, account_id)
    if email in result.get("success", []):
        return True, "邀请成功"
    
    failed = result.get("failed", [])
    for f in failed:
        if f.get("email") == email:
            return False, f.get("error", "Unknown error")
    
    return False, "Unknown error"
