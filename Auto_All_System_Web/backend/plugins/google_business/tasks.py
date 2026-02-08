"""
Celery异步任务
处理Google Business插件的后台任务
"""

import logging
from typing import List, Dict, Any

from celery import shared_task, group, chord
from django.db import transaction
from django.utils import timezone

from apps.cards.models import Card
from apps.integrations.google_accounts.models import GoogleAccount, GoogleAccountStatus
from .models import GoogleTask, GoogleTaskAccount, GoogleCardInfo
from .services import (
    browser_pool,
    GoogleLoginService,
    GoogleOneLinkService,
    SheerIDVerifyService,
    GoogleOneBindCardService,
)
from .utils import TaskLogger, EncryptionUtil, attach_playwright_trace

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_single_account(
    self,
    task_id: int,
    account_id: int,
    browser_id: str,
    ws_endpoint: str,
    task_type: str,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    处理单个账号的任务

    Args:
        self: Celery task实例
        task_id: 任务ID
        account_id: 账号ID
        browser_id: 浏览器ID
        ws_endpoint: WebSocket连接端点
        task_type: 任务类型 (login, get_link, verify, bind_card, one_click)
        config: 任务配置

    Returns:
        Dict: 处理结果
    """
    import asyncio
    import time
    from playwright.async_api import async_playwright

    task = GoogleTask.objects.get(id=task_id)
    task_account = GoogleTaskAccount.objects.get(task=task, account_id=account_id)

    # 账号信息（同步 ORM），避免在 async context 里触发 SynchronousOnlyOperation
    account = GoogleAccount.objects.get(id=account_id)

    # 解密密码
    try:
        password = EncryptionUtil.decrypt(account.password)
    except Exception as e:
        # 解密失败，可能是明文存储或 key 不匹配
        logger.warning(
            f"Password decryption failed for {account.email}: {e}, using raw value"
        )
        password = account.password

    # 解密 2FA 密钥
    try:
        secret = (
            EncryptionUtil.decrypt(account.two_fa_secret)
            if account.two_fa_secret
            else ""
        )
    except Exception as e:
        logger.warning(
            f"2FA secret decryption failed for {account.email}: {e}, using raw value"
        )
        secret = account.two_fa_secret or ""

    account_info = {
        "email": account.email,
        "password": password,
        "secret": secret,
        "backup": account.recovery_email or "",
    }

    sheerid_link_snapshot = getattr(account, "sheerid_link", "") or ""

    # 创建任务日志记录器（DB: GoogleTask.log + 文件: logs/trace/trace_<celery>_<email>.log）
    task_logger = TaskLogger(
        task,
        celery_task_id=getattr(self.request, "id", None),
        account_id=account_id,
        email=account.email,
        kind=f"google_{task_type}",
    )

    try:
        task_logger.info(
            f"[Account {account_id}] 开始处理账号 (任务类型: {task_type})..."
        )

        # 更新状态为运行中
        task_account.status = "processing"
        task_account.started_at = timezone.now()
        task_account.save()

        # 使用浏览器启动信息连接并执行任务
        async def _process():
            async with async_playwright() as playwright:

                async def _connect_with_retry(endpoint: str):
                    deadline = time.monotonic() + 30
                    last_err: Exception | None = None

                    while time.monotonic() < deadline:
                        try:
                            return await playwright.chromium.connect_over_cdp(endpoint)
                        except Exception as e:
                            last_err = e
                            await asyncio.sleep(1)

                    raise last_err or RuntimeError("connect_over_cdp timeout")

                browser = await _connect_with_retry(ws_endpoint)

                # connect_over_cdp 可能返回 0 个 contexts；做兼容兜底
                if browser.contexts:
                    context = browser.contexts[0]
                else:
                    context = await browser.new_context()

                page = context.pages[0] if context.pages else await context.new_page()

                # 自动记录页面导航/console/pageerror（尽量少侵入业务代码）
                attach_playwright_trace(page, task_logger)

                try:
                    result: Dict[str, Any]
                    keep_browser_open = False

                    if config.get("smoke_test_cdp_only") is True:
                        await page.goto("about:blank")
                        result = {
                            "success": True,
                            "message": "CDP 连接成功 (smoke_test_cdp_only)",
                        }

                    elif task_type == "login":
                        login_service = GoogleLoginService()
                        task_logger.event(
                            step="login",
                            action="start",
                            message="start login",
                            url=getattr(page, "url", ""),
                        )
                        result = await login_service.login(
                            page, account_info, task_logger
                        )
                        task_logger.event(
                            step="login",
                            action="result",
                            message="login finished",
                            url=getattr(page, "url", ""),
                            result={
                                "success": result.get("success"),
                                "message": result.get("message") or result.get("error"),
                            },
                        )

                    elif task_type == "get_link":
                        link_service = GoogleOneLinkService()
                        task_logger.event(
                            step="get_link",
                            action="start",
                            message="start get_verification_link",
                            url=getattr(page, "url", ""),
                        )
                        (
                            status,
                            link,
                            message,
                        ) = await link_service.get_verification_link(
                            page, account_info, task_logger
                        )
                        task_logger.event(
                            step="get_link",
                            action="result",
                            message="get_verification_link finished",
                            url=getattr(page, "url", ""),
                            result={
                                "status": status,
                                "has_link": bool(link),
                                "message": message,
                            },
                        )
                        result = {
                            "success": status
                            in ["link_ready", "verified", "subscribed"],
                            "status": status,
                            "link": link,
                            "message": message,
                            "account_updates": {"sheerid_link": link} if link else {},
                        }

                    elif task_type == "verify":
                        verify_service = SheerIDVerifyService(
                            api_key=config.get("api_key")
                        )
                        verification_id = SheerIDVerifyService.extract_verification_id(
                            sheerid_link_snapshot
                        )
                        if not verification_id:
                            raise Exception("No verification ID found")

                        results = verify_service.verify_batch(
                            [verification_id],
                            callback=lambda vid, msg: task_logger.info(msg),
                            task_logger=task_logger,
                        )
                        verify_result = results.get(verification_id, {})
                        ok = verify_result.get("status") == "success"
                        result = {
                            "success": ok,
                            "message": verify_result.get("message", "Unknown"),
                            "data": verify_result,
                            "account_updates": {"sheerid_verified": True} if ok else {},
                        }
                        task_logger.event(
                            step="verify",
                            action="result",
                            message="sheerid verify finished",
                            result={"success": ok, "message": result.get("message")},
                        )

                    elif task_type == "bind_card":
                        bind_service = GoogleOneBindCardService()
                        card = _select_card_for_task(task=task, config=config)
                        card_info = {
                            "number": card.card_number,
                            "exp_month": str(card.expiry_month).zfill(2),
                            "exp_year": str(card.expiry_year),
                            "cvv": card.cvv,
                        }

                        ok = False
                        message = ""
                        try:
                            ok, message = await bind_service.bind_and_subscribe(
                                page, card_info, account_info, task_logger
                            )
                        finally:
                            _mark_card_used(
                                card=card,
                                user=task.user,
                                success=ok,
                                purpose="google_one_bind_card",
                            )

                        suffix = (
                            f" (****{card.card_number[-4:]})"
                            if card.card_number
                            else ""
                        )

                        task_logger.event(
                            step="bind_card",
                            action="result",
                            message="bind_and_subscribe finished",
                            url=getattr(page, "url", ""),
                            result={
                                "success": ok,
                                "message": message,
                                "card": suffix.strip(),
                            },
                        )
                        result = {
                            "success": ok,
                            "message": f"{message}{suffix}",
                            "card_last4": card.card_number[-4:]
                            if card.card_number
                            else "",
                            "account_updates": {"card_bound": True} if ok else {},
                        }

                    elif task_type == "one_click":
                        task_logger.info(f"[Account {account_id}] 执行一键到底任务...")

                        meta = account.metadata or {}
                        google_one_status = str(meta.get("google_one_status") or "").lower()
                        gemini_status = str(account.gemini_status or "").lower()
                        sheerid_link_snapshot = account.sheerid_link or ""

                        force_rerun = bool(
                            config.get("force_rerun")
                            or config.get("force")
                            or config.get("rerun")
                        )
                        resume_mode = bool(config.get("resume", True)) and not force_rerun

                        has_link_status = google_one_status in [
                            "link_ready",
                            "verified",
                            "subscribed",
                            "ineligible",
                        ]
                        has_open_one = has_link_status or bool(sheerid_link_snapshot) or bool(account.sheerid_verified)
                        has_eligibility = has_link_status or bool(sheerid_link_snapshot) or bool(account.sheerid_verified)
                        has_verify = bool(account.sheerid_verified) or google_one_status in ["verified", "subscribed"]
                        has_subscribe = bool(account.card_bound) or gemini_status == "active" or google_one_status == "subscribed"
                        is_ineligible = google_one_status == "ineligible"

                        step2_needed = True
                        step3_needed = True
                        step4_needed = True
                        step5_needed = True

                        if resume_mode:
                            step2_needed = not has_open_one
                            step3_needed = not has_eligibility
                            step4_needed = not has_verify
                            step5_needed = not has_subscribe

                        if is_ineligible:
                            step4_needed = False
                            step5_needed = False

                        needs_security = bool(
                            config.get("security_change_2fa")
                            or config.get("security_new_recovery_email")
                            or config.get("new_recovery_email")
                            or config.get("new_email")
                        )
                        needs_login = step2_needed or step3_needed or step4_needed or step5_needed or needs_security

                        account_updates: Dict[str, Any] = {}

                        def append_note(note: str) -> None:
                            current = (account.notes or "").strip()
                            if note in current:
                                return
                            updated = f"{current}\n{note}".strip() if current else note
                            account_updates["notes"] = updated

                        # 主流程（6步）
                        # 1. 登录账号
                        if needs_login:
                            task_logger.info(f"[Account {account_id}] 步骤 1/6: 登录账号")
                            login_service = GoogleLoginService()
                            logged_in = await login_service.check_login_status(page)
                            if logged_in:
                                task_logger.info(f"[Account {account_id}] 已检测到登录态，跳过登录")
                                account_updates["status"] = GoogleAccountStatus.ACTIVE
                                account_updates["last_login_at"] = timezone.now()
                            else:
                                login_result = await login_service.login(
                                    page, account_info, task_logger, exit_on_captcha=True
                                )
                                if not login_result.get("success"):
                                    error_msg = login_result.get("error") or "登录失败"
                                    is_captcha = "机器人验证" in error_msg or "验证码" in error_msg
                                    if is_captcha:
                                        append_note("检测到机器人验证，已中断")
                                        account_updates["status"] = GoogleAccountStatus.LOCKED
                                        keep_browser_open = False
                                        error_msg = "需要机器人验证"
                                    if "手机号验证" in error_msg or "phone" in error_msg:
                                        append_note("需要手机号验证，需绑卡")
                                    main_flow_title = "机器人验证" if is_captcha else "登录失败"
                                    return {
                                        "success": False,
                                        "message": f"登录失败: {error_msg}",
                                        "account_updates": account_updates,
                                        "failed_step": "login",
                                        "main_flow_step_num": 1,
                                        "main_flow_step_title": main_flow_title,
                                         "keep_browser": False,
                                     }
                                account_updates["status"] = GoogleAccountStatus.ACTIVE
                                account_updates["last_login_at"] = timezone.now()
                        else:
                            task_logger.info(
                                f"[Account {account_id}] 步骤 1/6: 已完成，跳过"
                            )

                        # 2. 打开 Google One
                        if step2_needed:
                            task_logger.info(
                                f"[Account {account_id}] 步骤 2/6: 打开 Google One"
                            )
                            try:
                                await page.goto(
                                    "https://one.google.com/about/plans/ai-premium/student",
                                    wait_until="networkidle",
                                )
                                await asyncio.sleep(1)
                            except Exception:
                                # 不强依赖该跳转；后续 link_service 会自己导航
                                pass
                        else:
                            task_logger.info(
                                f"[Account {account_id}] 步骤 2/6: 已完成，跳过"
                            )

                        # 3. 检查学生资格（会获取 SheerID 链接/或判定已验证）
                        status = google_one_status
                        link = sheerid_link_snapshot

                        if step4_needed and not link:
                            step3_needed = True

                        if step3_needed:
                            task_logger.info(
                                f"[Account {account_id}] 步骤 3/6: 检查学生资格"
                            )
                            link_service = GoogleOneLinkService()
                            (
                                status,
                                link,
                                message,
                            ) = await link_service.get_verification_link(
                                page, account_info, task_logger
                            )
                            if status not in [
                                "link_ready",
                                "verified",
                                "subscribed",
                                "ineligible",
                            ]:
                                raise Exception(f"获取链接失败: {message}")
                        else:
                            task_logger.info(
                                f"[Account {account_id}] 步骤 3/6: 已完成，跳过"
                            )

                        if link:
                            account_updates["sheerid_link"] = link

                        if status in [
                            "link_ready",
                            "verified",
                            "subscribed",
                            "ineligible",
                        ]:
                            new_meta = dict(account.metadata or {})
                            new_meta["google_one_status"] = status
                            account_updates["metadata"] = new_meta

                        if status == "ineligible":
                            task_logger.info(
                                f"[Account {account_id}] 学生资格不符合，跳过后续验证/订阅"
                            )
                            new_meta = dict(account.metadata or {})
                            new_meta["google_one_status"] = "ineligible"
                            account_updates["metadata"] = new_meta
                            step4_needed = False
                            step5_needed = False

                        # 4. 学生验证（如果需要）
                        if step4_needed:
                            if status in ["verified", "subscribed"]:
                                task_logger.info(
                                    f"[Account {account_id}] 步骤 4/6: 已完成，跳过"
                                )
                            elif link:
                                task_logger.info(
                                    f"[Account {account_id}] 步骤 4/6: 学生验证"
                                )
                                verify_service = SheerIDVerifyService(
                                    api_key=config.get("api_key")
                                )
                                verification_id = (
                                    SheerIDVerifyService.extract_verification_id(link)
                                )
                                if verification_id:
                                    results = verify_service.verify_batch(
                                        [verification_id],
                                        callback=lambda vid, msg: task_logger.info(msg),
                                        task_logger=task_logger,
                                    )
                                    verify_result = results.get(verification_id, {})
                                    if verify_result.get("status") == "success":
                                        account_updates["sheerid_verified"] = True
                                    else:
                                        verify_message = str(
                                            verify_result.get("message") or "验证未成功"
                                        )
                                        task_logger.warning(
                                            f"[Account {account_id}] 验证未成功: {verify_message}"
                                        )
                                        if "HTTP 404" in verify_message:
                                            append_note("学生验证失败: HTTP 404")
                                            return {
                                                "success": False,
                                                "message": f"学生验证失败: {verify_message}",
                                                "account_updates": account_updates,
                                                "failed_step": "verify",
                                                "main_flow_step_num": 4,
                                                "main_flow_step_title": "学生验证失败",
                                                "keep_browser": False,
                                            }
                            else:
                                task_logger.info(
                                    f"[Account {account_id}] 步骤 4/6: 跳过（无验证链接）"
                                )
                        else:
                            task_logger.info(f"[Account {account_id}] 步骤 4/6: 跳过")

                        # 5. 订阅服务（绑卡订阅）
                        ok = True
                        message = ""
                        card_last4 = ""
                        if step5_needed:
                            task_logger.info(
                                f"[Account {account_id}] 步骤 5/6: 订阅服务"
                            )
                            bind_service = GoogleOneBindCardService()
                            card = _select_card_for_task(task=task, config=config)
                            card_info = {
                                "number": card.card_number,
                                "exp_month": str(card.expiry_month).zfill(2),
                                "exp_year": str(card.expiry_year),
                                "cvv": card.cvv,
                            }

                            try:
                                ok, message = await bind_service.bind_and_subscribe(
                                    page, card_info, account_info, task_logger
                                )
                            finally:
                                _mark_card_used(
                                    card=card,
                                    user=task.user,
                                    success=ok,
                                    purpose="google_one_one_click",
                                )

                            card_last4 = card.card_number[-4:] if card.card_number else ""
                        else:
                            task_logger.info(
                                f"[Account {account_id}] 步骤 5/6: 已完成，跳过"
                            )

                        suffix = f" (****{card_last4})" if card_last4 else ""
                        base_message = (
                            f"一键到底任务完成: {message}{suffix}"
                            if step5_needed
                            else "一键全自动续跑完成（已跳过完成步骤）"
                        )
                        result = {
                            "success": ok,
                            "message": base_message,
                            "card_last4": card_last4,
                            "account_updates": {
                                **account_updates,
                                **({"card_bound": True} if ok and step5_needed else {}),
                            },
                        }

                        # 6. 完成处理
                        task_logger.info(f"[Account {account_id}] 步骤 6/6: 完成处理")

                        # 主流程增项：安全设置（可选，默认关闭）
                        # - security_change_2fa: true
                        # - security_new_recovery_email: "xxx@xxx.com"
                        try:
                            from .services.security_service import GoogleSecurityService

                            security_service = GoogleSecurityService()

                            if config.get("security_change_2fa") is True:
                                task_logger.info(
                                    f"[Account {account_id}] 增项: 修改2FA"
                                )
                                (
                                    ok2,
                                    msg2,
                                    new_secret,
                                ) = await security_service.change_2fa_secret(
                                    page,
                                    {
                                        "email": account_info.get("email"),
                                        "password": account_info.get("password"),
                                        "totp_secret": account_info.get("secret") or "",
                                    },
                                )
                                if ok2 and new_secret:
                                    result.setdefault("extra", {})["new_2fa_secret"] = (
                                        new_secret
                                    )
                                else:
                                    task_logger.warning(
                                        f"[Account {account_id}] 增项修改2FA失败: {msg2}"
                                    )

                            new_recovery_email = (
                                config.get("security_new_recovery_email")
                                or config.get("new_recovery_email")
                                or config.get("new_email")
                            )
                            if (
                                isinstance(new_recovery_email, str)
                                and new_recovery_email.strip()
                            ):
                                task_logger.info(
                                    f"[Account {account_id}] 增项: 修改辅助邮箱"
                                )
                                (
                                    ok3,
                                    msg3,
                                ) = await security_service.change_recovery_email(
                                    page,
                                    {
                                        "email": account_info.get("email"),
                                        "password": account_info.get("password"),
                                        "totp_secret": account_info.get("secret") or "",
                                    },
                                    new_recovery_email.strip(),
                                )
                                if ok3:
                                    result.setdefault("account_updates", {})[
                                        "recovery_email"
                                    ] = new_recovery_email.strip()
                                else:
                                    task_logger.warning(
                                        f"[Account {account_id}] 增项修改辅助邮箱失败: {msg3}"
                                    )
                        except Exception as e:
                            # 增项不影响主流程结果，但要记录日志
                            task_logger.warning(
                                f"[Account {account_id}] 安全设置增项执行异常: {e}"
                            )

                    else:
                        raise Exception(f"Unknown task type: {task_type}")

                    return result

                finally:
                    # 断开连接/关闭窗口（按当前任务模型：跑完即关，避免大量窗口堆积）
                    # 但如果检测到机器人验证，保留浏览器让用户手动处理
                    if not keep_browser_open:
                        try:
                            await browser.close()
                        except Exception:
                            pass
                    else:
                        task_logger.info("检测到机器人验证，保留浏览器环境以便手动处理")

        # 运行异步函数（只做浏览器自动化，不做 ORM 写入）
        result = asyncio.run(_process())

        # best-effort: 关闭 GeekezBrowser 环境（避免批量跑完后大量窗口堆积）
        try:
            keep_browser = bool(
                isinstance(result, dict) and result.get("keep_browser") is True
            )
        except Exception:
            keep_browser = False

        if not keep_browser:
            try:
                from apps.integrations.geekez.api import GeekezBrowserAPI

                GeekezBrowserAPI().close_profile(str(browser_id))
            except Exception:
                pass

        # 把 trace 文件路径附加到结果，方便前端/排查定位
        trace_file = task_logger.trace_rel_path or (
            str(task_logger.trace_file) if task_logger.trace_file else ""
        )
        if isinstance(result, dict) and trace_file:
            result.setdefault("trace_file", trace_file)

        task_logger.event(
            step="task",
            action="result",
            message="process_single_account finished",
            level="info" if result.get("success") else "error",
            result={
                "success": bool(result.get("success")),
                "message": result.get("message"),
                "trace_file": trace_file,
            },
        )

        # === 以下为同步 ORM 更新（避免 SynchronousOnlyOperation） ===
        account_updates = result.pop("account_updates", None)
        extra = result.pop("extra", None)

        if isinstance(extra, dict) and extra.get("new_2fa_secret"):
            try:
                account_updates = dict(account_updates or {})
                account_updates["two_fa_secret"] = EncryptionUtil.encrypt(
                    str(extra["new_2fa_secret"])
                )
                account_updates["two_fa_enabled"] = True
            except Exception:
                logger.warning("Failed to apply new 2FA secret", exc_info=True)

        if isinstance(account_updates, dict) and account_updates:
            try:
                GoogleAccount.objects.filter(id=account_id).update(**account_updates)
            except Exception:
                logger.warning("Failed to apply account updates", exc_info=True)

        task_account.status = "success" if result.get("success") else "failed"
        task_account.completed_at = timezone.now()
        task_account.result_message = result.get("message", "")
        task_account.save(update_fields=["status", "completed_at", "result_message"])

        # 更新任务统计 + 完成态判断
        with transaction.atomic():
            locked_task = GoogleTask.objects.select_for_update().get(id=task_id)
            if result.get("success"):
                locked_task.success_count += 1
            else:
                locked_task.failed_count += 1

            done_count = GoogleTaskAccount.objects.filter(
                task_id=task_id,
                status__in=["success", "failed", "skipped"],
            ).count()
            if done_count >= locked_task.total_count:
                locked_task.status = (
                    "completed" if locked_task.success_count > 0 else "failed"
                )
                locked_task.completed_at = timezone.now()
            locked_task.save()

        task_logger.info(
            f"[Account {account_id}] ✅ 任务完成: {result.get('message', '')}"
        )

        return result

    except Exception as e:
        error_msg = f"[Account {account_id}] 处理失败: {str(e)}"
        task_logger.error(error_msg)
        logger.error(f"Task {task_id} account {account_id} failed: {e}", exc_info=True)

        # 更新任务账号状态为失败
        task_account.status = "failed"
        task_account.completed_at = timezone.now()
        task_account.error_message = str(e)
        task_account.save()

        # 更新任务统计 + 完成态判断
        with transaction.atomic():
            locked_task = GoogleTask.objects.select_for_update().get(id=task_id)
            locked_task.failed_count += 1

            done_count = GoogleTaskAccount.objects.filter(
                task_id=task_id, status__in=["success", "failed", "skipped"]
            ).count()
            if done_count >= locked_task.total_count:
                locked_task.status = (
                    "completed" if locked_task.success_count > 0 else "failed"
                )
                locked_task.completed_at = timezone.now()

            locked_task.save()

        # 重试逻辑
        if self.request.retries < self.max_retries:
            # 指数退避
            countdown = 2**self.request.retries
            raise self.retry(exc=e, countdown=countdown)

        # 不再重试：best-effort 关闭 GeekezBrowser 环境
        try:
            from apps.integrations.geekez.api import GeekezBrowserAPI

            GeekezBrowserAPI().close_profile(str(browser_id))
        except Exception:
            pass

        return {"success": False, "error": str(e)}


def _select_card_for_task(task: GoogleTask, config: Dict[str, Any]) -> Card:
    """根据任务配置从统一卡池挑选一张可用卡"""
    from datetime import date
    from django.db.models import Q, F

    card_pool = config.get("card_pool") or config.get("cardPool") or "public"
    strategy = config.get("card_strategy") or config.get("cardStrategy") or "sequential"

    today = date.today()

    with transaction.atomic():
        qs = Card.objects.select_for_update(skip_locked=True).filter(status="available")

        # pool_type 过滤
        if card_pool == "private":
            qs = qs.filter(pool_type="private", owner_user=task.user)
        else:
            qs = qs.filter(pool_type="public")

        # 未过期（简单判断）
        qs = qs.filter(
            Q(expiry_year__gt=today.year)
            | Q(expiry_year=today.year, expiry_month__gte=today.month)
        )

        # 使用次数限制：0=无限制
        qs = qs.filter(Q(max_use_count=0) | Q(use_count__lt=F("max_use_count")))

        # 排序策略
        if strategy == "random":
            qs = qs.order_by("?")
        elif strategy == "least_used":
            qs = qs.order_by("use_count", "last_used_at", "id")
        else:  # sequential
            qs = qs.order_by("last_used_at", "id")

        card = qs.first()
        if not card:
            raise RuntimeError(
                f"卡池中没有可用卡 (pool={card_pool}, strategy={strategy})"
            )

        # 预占用，避免并发任务重复选中同一卡
        card.status = "in_use"
        card.save(update_fields=["status"])
        return card


def _mark_card_used(card: Card, user, success: bool, purpose: str) -> None:
    """更新卡使用统计；失败也计 use_count，便于风控/轮换"""
    from django.utils import timezone
    from datetime import date

    try:
        card.use_count += 1
        if success:
            card.success_count += 1

        card.last_used_at = timezone.now()

        # 达到上限则标记为 used；否则释放回 available
        if (
            card.max_use_count
            and card.max_use_count > 0
            and card.use_count >= card.max_use_count
        ):
            card.status = "used"
        else:
            card.status = "available"

        # 过期标记（兜底）
        today = date.today()
        if card.expiry_year < today.year or (
            card.expiry_year == today.year and card.expiry_month < today.month
        ):
            card.status = "expired"

        card.save(
            update_fields=["use_count", "success_count", "last_used_at", "status"]
        )
    except Exception:
        logger.warning("Failed to update card usage", exc_info=True)


@shared_task
def batch_process_task(
    task_id: int, account_ids: List[int], task_type: str, config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    批量处理任务 (使用 GeekezBrowser)

    Args:
        task_id: 任务ID
        account_ids: 账号ID列表
        task_type: 任务类型 (one_click, verify, bind_card, get_link, login)
        config: 任务配置

    Returns:
        Dict: 批量处理结果
    """
    from apps.integrations.geekez.api import GeekezBrowserAPI, GeekezBrowserManager
    from .utils import EncryptionUtil

    task = GoogleTask.objects.get(id=task_id)
    task.status = "running"
    task.started_at = timezone.now()
    task.save()

    max_concurrency = int(config.get("max_concurrency") or config.get("concurrency") or 5)
    if max_concurrency <= 0:
        max_concurrency = 1
    # 任务启动错峰：避免同一时刻大量账号同时打开浏览器/请求 Google
    # stagger_seconds: 每个账号启动间隔（秒），默认 1s；可设为 2
    stagger_seconds = int(
        config.get("stagger_seconds")
        or config.get("stagger_delay")
        or config.get("start_stagger")
        or 1
    )
    if stagger_seconds < 0:
        stagger_seconds = 0

    logger.info(
        f"Starting batch task {task_id} with {len(account_ids)} accounts, type={task_type}, concurrency={max_concurrency}"
    )

    try:
        geek_api = GeekezBrowserAPI()
        geek_manager = GeekezBrowserManager(geek_api)

        # 检查 GeekezBrowser 是否在线
        if not geek_api.health_check():
            raise RuntimeError("GeekezBrowser 未运行，请先启动 GeekezBrowser 应用")

        # 确保启用远程调试
        geek_api.ensure_remote_debugging()

        # 创建子任务列表
        subtasks = []

        for index, account_id in enumerate(account_ids):
            try:
                # 获取账号信息
                account = GoogleAccount.objects.get(id=account_id)
                task_account = GoogleTaskAccount.objects.get(
                    task=task, account_id=account_id
                )

                # 解密密码
                try:
                    password = EncryptionUtil.decrypt(account.password)
                except Exception as e:
                    logger.warning(
                        f"Password decryption failed for {account.email}: {e}, using raw value"
                    )
                    password = account.password  # 可能未加密

                # 解密 2FA 密钥
                try:
                    two_fa_secret = (
                        EncryptionUtil.decrypt(account.two_fa_secret)
                        if getattr(account, "two_fa_secret", "")
                        else ""
                    )
                except Exception as e:
                    logger.warning(
                        f"2FA secret decryption failed for {account.email}: {e}, using raw value"
                    )
                    two_fa_secret = getattr(account, "two_fa_secret", "") or ""

                # 准备账号信息
                account_info = {
                    "email": account.email,
                    "password": password,
                    "recovery_email": account.recovery_email or "",
                    "2fa_secret": two_fa_secret,
                }

                # 创建/更新 Profile
                profile = geek_manager.ensure_profile_for_account(
                    email=account.email,
                    account_info=account_info,
                    proxy=None,  # TODO: 从配置或账号获取代理
                )

                # 启动浏览器
                launch_info = geek_manager.launch_by_email(account.email)
                if not launch_info:
                    logger.error(f"Failed to launch browser for {account.email}")
                    task_account.status = "failed"
                    task_account.error_message = "无法启动浏览器"
                    task_account.save()
                    continue

                # 优先使用 ws_endpoint（launch_profile 已做 host rewrite），没有则退回 http cdp_endpoint
                ws_endpoint = launch_info.ws_endpoint or launch_info.cdp_endpoint

                # 更新 task_account 的浏览器信息
                task_account.browser_id = profile.id
                task_account.save()

                # 创建子任务
                delay_seconds = index * stagger_seconds
                subtask = (
                    process_single_account.s(
                        task_id, account_id, profile.id, ws_endpoint, task_type, config
                    )
                    .set(countdown=delay_seconds)
                )
                subtasks.append(subtask)

            except GoogleAccount.DoesNotExist:
                logger.error(f"Account {account_id} not found")
                continue
            except Exception as e:
                logger.error(
                    f"Error preparing account {account_id}: {e}", exc_info=True
                )
                try:
                    task_account = GoogleTaskAccount.objects.get(
                        task=task, account_id=account_id
                    )
                    task_account.status = "failed"
                    task_account.error_message = str(e)
                    task_account.save()
                except Exception:
                    pass
                continue

        # 并发执行子任务（使用group）
        if subtasks:
            job = group(subtasks)
            result = job.apply_async()
            logger.info(f"Started {len(subtasks)} subtasks for task {task_id}")
        else:
            # 没有成功启动的子任务
            task.status = "failed"
            task.completed_at = timezone.now()
            task.error_message = "没有可执行的账号"
            task.save()
            return {"success": False, "task_id": task_id, "error": "没有可执行的账号"}

        # 注意：不在这里标记完成，由子任务完成后更新
        # 检查是否所有子任务都立即失败了
        if len(subtasks) == 0:
            task.status = "completed"
            task.completed_at = timezone.now()
            task.save()

        logger.info(f"Batch task {task_id} dispatched")

        return {
            "success": True,
            "task_id": task_id,
            "total": len(account_ids),
            "started": len(subtasks),
        }

    except Exception as e:
        logger.error(f"Batch task {task_id} failed: {e}", exc_info=True)

        task.status = "failed"
        task.completed_at = timezone.now()
        task.error_message = str(e)
        task.save()

        return {"success": False, "task_id": task_id, "error": str(e)}


@shared_task
def cleanup_browser_pool():
    """
    清理浏览器资源池（定期任务）
    """
    import asyncio

    logger.info("Running browser pool cleanup...")

    try:
        asyncio.run(browser_pool.cleanup_all())
        logger.info("Browser pool cleanup completed")
        return {"success": True}
    except Exception as e:
        logger.error(f"Browser pool cleanup failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@shared_task
def update_task_statistics(task_id: int):
    """
    更新任务统计信息

    Args:
        task_id: 任务ID
    """
    try:
        task = GoogleTask.objects.get(id=task_id)

        # 统计各状态的账号数量
        task_accounts = GoogleTaskAccount.objects.filter(task=task)

        total_count = task_accounts.count()
        success_count = task_accounts.filter(status="completed").count()
        failed_count = task_accounts.filter(status="failed").count()
        skipped_count = task_accounts.filter(status="skipped").count()

        # 更新任务
        task.total_count = total_count
        task.success_count = success_count
        task.failed_count = failed_count
        task.skipped_count = skipped_count
        task.save()

        logger.info(f"Updated statistics for task {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "statistics": {
                "total": total_count,
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
            },
        }

    except Exception as e:
        logger.error(f"Failed to update task statistics: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==================== 安全设置任务 ====================


@shared_task(bind=True, name="google_business.security_change_2fa")
def security_change_2fa_task(
    self,
    account_ids: list,
    user_id: int,
    browser_type: str | None = None,
):
    """
    修改 2FA 密钥任务
    """
    import asyncio

    from .services import browser_pool
    from .services.security_service import GoogleSecurityService
    from apps.integrations.browser_base import BrowserType

    logger.info(f"Starting 2FA change task for {len(account_ids)} accounts")

    bt = BrowserType(browser_type) if browser_type else None
    security_service = GoogleSecurityService(browser_type=bt)
    results = []

    # 防止任务长期卡在 PROGRESS：按账号级别设置硬超时
    per_account_timeout_s = 300

    for i, account_id in enumerate(account_ids):
        try:
            account = GoogleAccount.objects.get(id=account_id)

            task_logger = TaskLogger(
                None,
                celery_task_id=str(self.request.id),
                account_id=account_id,
                email=account.email,
                kind="security_change_2fa",
            )
            task_logger.event(
                step="task",
                action="start",
                message="start security_change_2fa",
            )

            try:
                password = EncryptionUtil.decrypt(account.password)
            except Exception:
                password = account.password

            try:
                totp_secret = (
                    EncryptionUtil.decrypt(account.two_fa_secret)
                    if account.two_fa_secret
                    else ""
                )
            except Exception:
                totp_secret = account.two_fa_secret or ""

            account_info = {
                "email": account.email,
                "password": password,
                "totp_secret": totp_secret,
            }

            metadata = account.metadata or {}
            profile_id = None
            if isinstance(metadata, dict):
                geekez_profile = metadata.get("geekez_profile")
                if isinstance(geekez_profile, dict):
                    profile_id = geekez_profile.get("profile_id")

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(account_ids),
                    "email": account.email,
                },
            )

            # 重要：Playwright 对象绑定 event loop，必须在同一个 asyncio.run() 生命周期内
            # 完成 acquire -> login -> action -> release，避免跨 loop 使用导致挂死。
            async def run_all():
                instance = None
                used_profile_id = None

                if profile_id:
                    instance = await browser_pool.acquire_by_profile_id(
                        profile_id=str(profile_id),
                        task_id=str(self.request.id),
                        browser_type=bt,
                    )
                    if instance:
                        used_profile_id = str(profile_id)
                    else:
                        task_logger.event(
                            step="browser",
                            action="acquire",
                            level="warning",
                            message=f"failed to acquire by profile_id: {profile_id}, fallback to email",
                        )

                if not instance:
                    instance = await browser_pool.acquire_by_email(
                        email=account.email,
                        task_id=str(self.request.id),
                        account_info=account_info,
                        browser_type=bt,
                    )
                if not instance or not instance.page:
                    task_logger.event(
                        step="browser",
                        action="acquire",
                        level="error",
                        message="failed to acquire browser instance",
                    )
                    return False, "无法获取浏览器实例", None

                try:
                    attach_playwright_trace(instance.page, task_logger)

                    login_service = GoogleLoginService()
                    try:
                        logged_in = await login_service.check_login_status(
                            instance.page
                        )
                    except Exception:
                        logged_in = False

                    if not logged_in:
                        task_logger.event(
                            step="login",
                            action="start",
                            message="start login",
                            url=getattr(instance.page, "url", ""),
                        )
                        login_res = await login_service.login(
                            instance.page,
                            {
                                "email": account.email,
                                "password": password,
                                "secret": totp_secret,
                                "backup": account.recovery_email or "",
                            },
                            task_logger,
                        )
                        if not login_res.get("success"):
                            err = (
                                login_res.get("error") or login_res.get("message") or ""
                            )
                            task_logger.event(
                                step="login",
                                action="result",
                                level="error",
                                message="login failed",
                                url=getattr(instance.page, "url", ""),
                                result={"error": err},
                            )
                            return False, f"登录失败: {err}", None

                        task_logger.event(
                            step="login",
                            action="result",
                            message="login ok",
                            url=getattr(instance.page, "url", ""),
                        )

                    return await security_service.change_2fa_secret(
                        instance.page,
                        account_info,
                        task_logger=task_logger,
                    )
                finally:
                    try:
                        if used_profile_id:
                            await asyncio.wait_for(
                                asyncio.shield(
                                    browser_pool.release(
                                        used_profile_id,
                                        close=True,
                                    )
                                ),
                                timeout=30,
                            )
                        else:
                            await asyncio.wait_for(
                                asyncio.shield(
                                    browser_pool.release_by_email(
                                        account.email,
                                        browser_type=bt,
                                        close=True,
                                    )
                                ),
                                timeout=30,
                            )
                    except Exception:
                        logger.warning(
                            "Failed to release browser instance (2fa)",
                            exc_info=True,
                        )

            async def run_with_timeout():
                return await asyncio.wait_for(run_all(), timeout=per_account_timeout_s)

            try:
                ok, msg, new_secret = asyncio.run(run_with_timeout())
            except asyncio.TimeoutError:
                ok, msg, new_secret = False, "任务超时", None

            # 把 trace 文件路径回传给前端，方便按账号排查
            trace_file = task_logger.trace_rel_path or (
                str(task_logger.trace_file) if task_logger.trace_file else ""
            )

            task_logger.event(
                step="task",
                action="result",
                message="security_change_2fa finished",
                level="info" if ok else "error",
                result={
                    "success": ok,
                    "message": msg,
                    "new_secret_masked": TaskLogger._mask_secret(new_secret)
                    if new_secret
                    else "",
                    "trace_file": trace_file,
                },
            )

            # 登录失败时补写账号状态，避免前端列表保持灰色 pending。
            if (not ok) and isinstance(msg, str) and msg.startswith("登录失败"):
                fail_note = msg.strip() or "登录失败"
                current_notes = (account.notes or "").strip()
                if fail_note not in current_notes:
                    account.notes = (
                        f"{current_notes}\n{fail_note}".strip()
                        if current_notes
                        else fail_note
                    )
                account.status = GoogleAccountStatus.LOCKED
                account.save(update_fields=["status", "notes"])

            if ok and new_secret:
                # 更新数据库
                account.two_fa_secret = EncryptionUtil.encrypt(new_secret)
                account.two_fa_enabled = True

                # 同时把“新2FA”写入账号 metadata，方便在账号列表直接查看/复制
                # 注意：这里存的是明文，属于敏感信息。
                # 后续如需增强安全性，可改为只保存掩码或保存加密值。
                meta = account.metadata or {}
                meta["new_2fa_secret"] = new_secret
                # 额外保存一份“Google 展示风格”的 2FA（小写 + 每 4 位一组空格）
                # 例：e2cv z6er 5v55 zfox ...（spaces don't matter）
                try:
                    s = (new_secret or "").replace(" ", "").strip().lower()
                    meta["new_2fa_secret_display"] = " ".join(
                        [s[i : i + 4] for i in range(0, len(s), 4)]
                    )
                except Exception:
                    meta["new_2fa_secret_display"] = None
                meta["new_2fa_updated_at"] = timezone.now().isoformat()
                account.metadata = meta

                account.save(
                    update_fields=["two_fa_secret", "two_fa_enabled", "metadata"]
                )

            results.append(
                {
                    "email": account.email,
                    "success": ok,
                    "message": msg,
                    "new_secret": new_secret if ok else None,
                    "trace_file": trace_file,
                }
            )

        except Exception as e:
            logger.error(
                f"2FA change failed for account {account_id}: {e}", exc_info=True
            )
            results.append(
                {
                    "account_id": account_id,
                    "success": False,
                    "message": str(e),
                }
            )
        finally:
            # release 已在 run_all() 内完成
            pass

    return {
        "success": True,
        "results": results,
        "total": len(account_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
    }


@shared_task(bind=True, name="google_business.security_change_recovery_email")
def security_change_recovery_email_task(
    self,
    account_ids: list,
    new_email: str,
    user_id: int,
    browser_type: str | None = None,
):
    """
    修改辅助邮箱任务
    """
    import asyncio

    from .services import browser_pool
    from .services.security_service import GoogleSecurityService
    from apps.integrations.browser_base import BrowserType

    logger.info(f"Starting recovery email change task for {len(account_ids)} accounts")

    bt = BrowserType(browser_type) if browser_type else None
    security_service = GoogleSecurityService(browser_type=bt)
    results = []

    # 防止任务长期卡在 PROGRESS：按账号级别设置硬超时
    per_account_timeout_s = 300

    for i, account_id in enumerate(account_ids):
        try:
            account = GoogleAccount.objects.get(id=account_id)

            task_logger = TaskLogger(
                None,
                celery_task_id=str(self.request.id),
                account_id=account_id,
                email=account.email,
                kind="security_change_recovery_email",
            )
            task_logger.event(
                step="task",
                action="start",
                message=f"start security_change_recovery_email -> {new_email}",
            )

            try:
                password = EncryptionUtil.decrypt(account.password)
            except Exception:
                password = account.password

            try:
                totp_secret = (
                    EncryptionUtil.decrypt(account.two_fa_secret)
                    if account.two_fa_secret
                    else ""
                )
            except Exception:
                totp_secret = account.two_fa_secret or ""

            account_info = {
                "email": account.email,
                "password": password,
                "totp_secret": totp_secret,
            }

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(account_ids),
                    "email": account.email,
                },
            )

            # 重要：Playwright 对象绑定 event loop，必须在同一个 asyncio.run() 生命周期内
            # 完成 acquire -> login -> action -> release，避免跨 loop 使用导致挂死。
            async def run_all():
                instance = await browser_pool.acquire_by_email(
                    email=account.email,
                    task_id=str(self.request.id),
                    account_info=account_info,
                    browser_type=bt,
                )
                if not instance or not instance.page:
                    task_logger.event(
                        step="browser",
                        action="acquire",
                        level="error",
                        message="failed to acquire browser instance",
                    )
                    return False, "无法获取浏览器实例"

                try:
                    attach_playwright_trace(instance.page, task_logger)

                    login_service = GoogleLoginService()
                    try:
                        logged_in = await login_service.check_login_status(
                            instance.page
                        )
                    except Exception:
                        logged_in = False

                    if not logged_in:
                        task_logger.event(
                            step="login",
                            action="start",
                            message="start login",
                            url=getattr(instance.page, "url", ""),
                        )
                        login_res = await login_service.login(
                            instance.page,
                            {
                                "email": account.email,
                                "password": password,
                                "secret": totp_secret,
                                "backup": account.recovery_email or "",
                            },
                            task_logger,
                        )
                        if not login_res.get("success"):
                            err = (
                                login_res.get("error") or login_res.get("message") or ""
                            )
                            task_logger.event(
                                step="login",
                                action="result",
                                level="error",
                                message="login failed",
                                url=getattr(instance.page, "url", ""),
                                result={"error": err},
                            )
                            return False, f"登录失败: {err}"

                        task_logger.event(
                            step="login",
                            action="result",
                            message="login ok",
                            url=getattr(instance.page, "url", ""),
                        )

                    return await security_service.change_recovery_email(
                        instance.page,
                        account_info,
                        new_email,
                        task_logger=task_logger,
                    )
                finally:
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(
                                browser_pool.release_by_email(
                                    account.email,
                                    browser_type=bt,
                                    close=True,
                                )
                            ),
                            timeout=30,
                        )
                    except Exception:
                        logger.warning(
                            "Failed to release browser instance (recovery email)",
                            exc_info=True,
                        )

            async def run_with_timeout():
                return await asyncio.wait_for(run_all(), timeout=per_account_timeout_s)

            try:
                ok, msg = asyncio.run(run_with_timeout())
            except asyncio.TimeoutError:
                ok, msg = False, "任务超时"

            trace_file = task_logger.trace_rel_path or (
                str(task_logger.trace_file) if task_logger.trace_file else ""
            )
            task_logger.event(
                step="task",
                action="result",
                message="security_change_recovery_email finished",
                level="info" if ok else "error",
                result={"success": ok, "message": msg, "trace_file": trace_file},
            )

            if ok:
                account.recovery_email = new_email
                account.save(update_fields=["recovery_email"])

            results.append(
                {
                    "email": account.email,
                    "success": ok,
                    "message": msg,
                    "trace_file": trace_file,
                }
            )

        except Exception as e:
            logger.error(
                f"Recovery email change failed for account {account_id}: {e}",
                exc_info=True,
            )
            results.append(
                {
                    "account_id": account_id,
                    "success": False,
                    "message": str(e),
                }
            )
        finally:
            # release 已在 run_all() 内完成
            pass

    return {
        "success": True,
        "results": results,
        "total": len(account_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
    }


@shared_task(bind=True, name="google_business.security_get_backup_codes")
def security_get_backup_codes_task(
    self,
    account_ids: list,
    user_id: int,
    browser_type: str | None = None,
):
    """
    获取备份验证码任务
    """
    import asyncio

    from .services import browser_pool
    from .services.security_service import GoogleSecurityService
    from apps.integrations.browser_base import BrowserType

    logger.info(f"Starting backup codes task for {len(account_ids)} accounts")

    bt = BrowserType(browser_type) if browser_type else None
    security_service = GoogleSecurityService(browser_type=bt)
    results = []

    # 防止任务长期卡在 PROGRESS：按账号级别设置硬超时
    per_account_timeout_s = 300

    for i, account_id in enumerate(account_ids):
        email_for_release = None
        try:
            account = GoogleAccount.objects.get(id=account_id)
            email_for_release = account.email

            task_logger = TaskLogger(
                None,
                celery_task_id=str(self.request.id),
                account_id=account_id,
                email=account.email,
                kind="security_get_backup_codes",
            )
            task_logger.event(
                step="task",
                action="start",
                message="start security_get_backup_codes",
            )

            try:
                password = EncryptionUtil.decrypt(account.password)
            except Exception:
                password = account.password

            try:
                totp_secret = (
                    EncryptionUtil.decrypt(account.two_fa_secret)
                    if account.two_fa_secret
                    else ""
                )
            except Exception:
                totp_secret = account.two_fa_secret or ""

            account_info = {
                "email": account.email,
                "password": password,
                "totp_secret": totp_secret,
            }

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(account_ids),
                    "email": account.email,
                },
            )

            # 重要：Playwright 对象绑定 event loop，必须在同一个 asyncio.run() 生命周期内
            # 完成 acquire -> login -> action -> release，避免跨 loop 使用导致挂死。
            async def run_all():
                instance = await browser_pool.acquire_by_email(
                    email=account.email,
                    task_id=str(self.request.id),
                    account_info=account_info,
                    browser_type=bt,
                )
                if not instance or not instance.page:
                    task_logger.event(
                        step="browser",
                        action="acquire",
                        level="error",
                        message="failed to acquire browser instance",
                    )
                    return False, "无法获取浏览器实例", []

                try:
                    attach_playwright_trace(instance.page, task_logger)

                    login_service = GoogleLoginService()
                    try:
                        logged_in = await login_service.check_login_status(
                            instance.page
                        )
                    except Exception:
                        logged_in = False

                    if not logged_in:
                        task_logger.event(
                            step="login",
                            action="start",
                            message="start login",
                            url=getattr(instance.page, "url", ""),
                        )
                        login_res = await login_service.login(
                            instance.page,
                            {
                                "email": account.email,
                                "password": password,
                                "secret": totp_secret,
                                "backup": account.recovery_email or "",
                            },
                            task_logger,
                        )
                        if not login_res.get("success"):
                            err = (
                                login_res.get("error") or login_res.get("message") or ""
                            )
                            task_logger.event(
                                step="login",
                                action="result",
                                level="error",
                                message="login failed",
                                url=getattr(instance.page, "url", ""),
                                result={"error": err},
                            )
                            return False, f"登录失败: {err}", []

                        task_logger.event(
                            step="login",
                            action="result",
                            message="login ok",
                            url=getattr(instance.page, "url", ""),
                        )

                    return await security_service.get_backup_codes(
                        instance.page,
                        account_info,
                        task_logger=task_logger,
                    )
                finally:
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(
                                browser_pool.release_by_email(
                                    account.email,
                                    browser_type=bt,
                                    close=True,
                                )
                            ),
                            timeout=30,
                        )
                    except Exception:
                        logger.warning(
                            "Failed to release browser instance (backup codes)",
                            exc_info=True,
                        )

            async def run_with_timeout():
                return await asyncio.wait_for(run_all(), timeout=per_account_timeout_s)

            try:
                ok, msg, codes = asyncio.run(run_with_timeout())
            except asyncio.TimeoutError:
                ok, msg, codes = False, "任务超时", []

            trace_file = task_logger.trace_rel_path or (
                str(task_logger.trace_file) if task_logger.trace_file else ""
            )
            task_logger.event(
                step="task",
                action="result",
                message="security_get_backup_codes finished",
                level="info" if ok else "error",
                result={
                    "success": ok,
                    "message": msg,
                    "codes_count": len(codes or []),
                    "trace_file": trace_file,
                },
            )

            results.append(
                {
                    "email": account.email,
                    "success": ok,
                    "message": msg,
                    "backup_codes": codes if ok else [],
                    "trace_file": trace_file,
                }
            )

        except Exception as e:
            logger.error(
                f"Backup codes failed for account {account_id}: {e}", exc_info=True
            )
            results.append(
                {
                    "account_id": account_id,
                    "success": False,
                    "message": str(e),
                }
            )
        finally:
            # release 已在 run_all() 内完成
            pass

    return {
        "success": True,
        "results": results,
        "total": len(account_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
    }


@shared_task(bind=True, name="google_business.security_one_click")
def security_one_click_task(
    self,
    account_ids: list,
    new_recovery_email: str | None = None,
    user_id: int | None = None,
    browser_type: str | None = None,
):
    """
    一键安全设置任务
    """
    import asyncio

    from .services import browser_pool
    from .services.security_service import GoogleSecurityService
    from apps.integrations.browser_base import BrowserType

    logger.info(f"Starting one-click security task for {len(account_ids)} accounts")

    bt = BrowserType(browser_type) if browser_type else None
    security_service = GoogleSecurityService(browser_type=bt)
    results = []

    # 一键会做多步动作，给更长超时但仍防止无限等待
    per_account_timeout_s = 420

    for i, account_id in enumerate(account_ids):
        try:
            account = GoogleAccount.objects.get(id=account_id)

            try:
                password = EncryptionUtil.decrypt(account.password)
            except Exception:
                password = account.password

            try:
                totp_secret = (
                    EncryptionUtil.decrypt(account.two_fa_secret)
                    if account.two_fa_secret
                    else ""
                )
            except Exception:
                totp_secret = account.two_fa_secret or ""

            account_info = {
                "email": account.email,
                "password": password,
                "totp_secret": totp_secret,
            }

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(account_ids),
                    "email": account.email,
                },
            )

            # 重要：Playwright 对象绑定 event loop，必须在同一个 asyncio.run() 生命周期内
            # 完成 acquire -> login -> action -> release，避免跨 loop 使用导致挂死。
            async def run_all():
                instance = await browser_pool.acquire_by_email(
                    email=account.email,
                    task_id=str(self.request.id),
                    account_info=account_info,
                    browser_type=bt,
                )
                if not instance or not instance.page:
                    task_logger.event(
                        step="browser",
                        action="acquire",
                        level="error",
                        message="failed to acquire browser instance",
                    )
                    return False, "无法获取浏览器实例", None

                try:
                    attach_playwright_trace(instance.page, task_logger)

                    login_service = GoogleLoginService()
                    try:
                        logged_in = await login_service.check_login_status(
                            instance.page
                        )
                    except Exception:
                        logged_in = False

                    if not logged_in:
                        task_logger.event(
                            step="login",
                            action="start",
                            message="start login",
                            url=getattr(instance.page, "url", ""),
                        )
                        login_res = await login_service.login(
                            instance.page,
                            {
                                "email": account.email,
                                "password": password,
                                "secret": totp_secret,
                                "backup": account.recovery_email or "",
                            },
                            task_logger,
                        )
                        if not login_res.get("success"):
                            err = (
                                login_res.get("error") or login_res.get("message") or ""
                            )
                            task_logger.event(
                                step="login",
                                action="result",
                                level="error",
                                message="login failed",
                                url=getattr(instance.page, "url", ""),
                                result={"error": err},
                            )
                            return False, f"登录失败: {err}", None

                        task_logger.event(
                            step="login",
                            action="result",
                            message="login ok",
                            url=getattr(instance.page, "url", ""),
                        )

                    return await security_service.one_click_security_update(
                        instance.page,
                        account_info,
                        new_recovery_email,
                        task_logger=task_logger,
                    )
                finally:
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(
                                browser_pool.release_by_email(
                                    account.email,
                                    browser_type=bt,
                                    close=True,
                                )
                            ),
                            timeout=30,
                        )
                    except Exception:
                        logger.warning(
                            "Failed to release browser instance (one click security)",
                            exc_info=True,
                        )

            async def run_with_timeout():
                return await asyncio.wait_for(run_all(), timeout=per_account_timeout_s)

            try:
                ok, msg, data = asyncio.run(run_with_timeout())
            except asyncio.TimeoutError:
                ok, msg, data = False, "任务超时", None

            trace_file = task_logger.trace_rel_path or (
                str(task_logger.trace_file) if task_logger.trace_file else ""
            )
            task_logger.event(
                step="task",
                action="result",
                message="security_one_click finished",
                level="info" if ok else "error",
                result={
                    "success": ok,
                    "message": msg,
                    "has_data": bool(data),
                    "trace_file": trace_file,
                },
            )

            # 更新数据库
            if ok and data:
                update_fields = []
                if data.get("new_2fa_secret"):
                    account.two_fa_secret = EncryptionUtil.encrypt(
                        data["new_2fa_secret"]
                    )
                    account.two_fa_enabled = True
                    update_fields.extend(["two_fa_secret", "two_fa_enabled"])
                if data.get("new_recovery_email"):
                    account.recovery_email = data["new_recovery_email"]
                    update_fields.append("recovery_email")
                if update_fields:
                    account.save(update_fields=list(set(update_fields)))

            results.append(
                {
                    "email": account.email,
                    "success": ok,
                    "message": msg,
                    "data": data if ok else None,
                    "trace_file": trace_file,
                }
            )

        except Exception as e:
            logger.error(
                f"One-click security failed for account {account_id}: {e}",
                exc_info=True,
            )
            results.append(
                {
                    "account_id": account_id,
                    "success": False,
                    "message": str(e),
                }
            )
        finally:
            # release 已在 run_all() 内完成
            pass

    return {
        "success": True,
        "results": results,
        "total": len(account_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
    }


# ==================== 订阅验证任务 ====================


@shared_task(bind=True, name="google_business.subscription_verify_status")
def subscription_verify_status_task(
    self,
    account_ids: list,
    take_screenshot: bool = True,
    user_id: int | None = None,
    browser_type: str | None = None,
):
    """
    验证订阅状态任务
    """
    import asyncio

    from .services import browser_pool
    from .services.subscription_service import SubscriptionVerifyService
    from apps.integrations.browser_base import BrowserType

    logger.info(f"Starting subscription verify task for {len(account_ids)} accounts")

    bt = BrowserType(browser_type) if browser_type else None
    subscription_service = SubscriptionVerifyService()
    results = []

    per_account_timeout_s = 240

    for i, account_id in enumerate(account_ids):
        email_for_release = None
        try:
            account = GoogleAccount.objects.get(id=account_id)
            email_for_release = account.email

            task_logger = TaskLogger(
                None,
                celery_task_id=str(self.request.id),
                account_id=account_id,
                email=account.email,
                kind="subscription_verify_status",
            )
            task_logger.event(
                step="task",
                action="start",
                message="start subscription_verify_status",
                result={"take_screenshot": bool(take_screenshot)},
            )

            try:
                password = EncryptionUtil.decrypt(account.password)
            except Exception:
                password = account.password

            try:
                totp_secret = (
                    EncryptionUtil.decrypt(account.two_fa_secret)
                    if account.two_fa_secret
                    else ""
                )
            except Exception:
                totp_secret = account.two_fa_secret or ""

            # subscription_service 本身只需要 email，但我们需要先确保登录态
            account_info = {
                "email": account.email,
                "password": password,
                "totp_secret": totp_secret,
            }

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(account_ids),
                    "email": account.email,
                },
            )

            # 重要：Playwright 对象绑定 event loop，必须在同一 asyncio.run() 生命周期内
            # 完成 acquire -> login -> action -> release，避免跨 loop 使用导致挂死。
            async def run_all():
                instance = await browser_pool.acquire_by_email(
                    email=account.email,
                    task_id=str(self.request.id),
                    account_info=account_info,
                    browser_type=bt,
                )
                if not instance or not instance.page:
                    task_logger.event(
                        step="browser",
                        action="acquire",
                        level="error",
                        message="failed to acquire browser instance",
                    )
                    return False, {"error": "无法获取浏览器实例"}, None

                try:
                    attach_playwright_trace(instance.page, task_logger)

                    login_service = GoogleLoginService()
                    try:
                        logged_in = await login_service.check_login_status(
                            instance.page
                        )
                    except Exception:
                        logged_in = False

                    if not logged_in:
                        task_logger.event(
                            step="login",
                            action="start",
                            message="start login",
                            url=getattr(instance.page, "url", ""),
                        )
                        login_res = await login_service.login(
                            instance.page,
                            {
                                "email": account.email,
                                "password": password,
                                "secret": totp_secret,
                                "backup": account.recovery_email or "",
                            },
                            task_logger,
                        )
                        if not login_res.get("success"):
                            err = (
                                login_res.get("error") or login_res.get("message") or ""
                            )
                            task_logger.event(
                                step="login",
                                action="result",
                                level="error",
                                message="login failed",
                                url=getattr(instance.page, "url", ""),
                                result={"error": err},
                            )
                            return False, {"error": f"登录失败: {err}"}, None

                        task_logger.event(
                            step="login",
                            action="result",
                            message="login ok",
                            url=getattr(instance.page, "url", ""),
                        )

                    return await subscription_service.verify_subscription_status(
                        instance.page,
                        account_info,
                        take_screenshot=take_screenshot,
                    )
                finally:
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(
                                browser_pool.release_by_email(
                                    account.email,
                                    browser_type=bt,
                                    close=True,
                                )
                            ),
                            timeout=30,
                        )
                    except Exception:
                        logger.warning(
                            "Failed to release browser instance (subscription verify)",
                            exc_info=True,
                        )

            async def run_with_timeout():
                return await asyncio.wait_for(run_all(), timeout=per_account_timeout_s)

            try:
                ok, status_info, screenshot_path = asyncio.run(run_with_timeout())
            except asyncio.TimeoutError:
                ok, status_info, screenshot_path = False, {"error": "任务超时"}, None

            trace_file = task_logger.trace_rel_path or (
                str(task_logger.trace_file) if task_logger.trace_file else ""
            )
            task_logger.event(
                step="task",
                action="result",
                message="subscription_verify_status finished",
                level="info" if ok else "error",
                result={
                    "success": ok,
                    "status": status_info.get("status")
                    if isinstance(status_info, dict)
                    else None,
                    "screenshot": screenshot_path or "",
                    "trace_file": trace_file,
                },
            )

            # 更新账号元信息（不要写到 account.status 字段：该字段是账号生命周期状态，choices 不兼容）
            if ok and isinstance(status_info, dict) and status_info.get("status"):
                status_value = status_info.get("status")
                meta = account.metadata or {}
                meta["google_one_status"] = status_value
                meta["google_one_status_info"] = status_info
                if screenshot_path:
                    meta["google_one_screenshot"] = screenshot_path
                account.metadata = meta

                update_fields = ["metadata"]
                if status_value == "subscribed":
                    account.gemini_status = "active"
                    update_fields.append("gemini_status")
                if status_value == "verified":
                    account.sheerid_verified = True
                    update_fields.append("sheerid_verified")
                account.save(update_fields=list(set(update_fields)))

            results.append(
                {
                    "email": account.email,
                    "success": ok,
                    "status": status_info,
                    "screenshot": screenshot_path,
                    "trace_file": trace_file,
                }
            )

        except Exception as e:
            logger.error(
                f"Subscription verify failed for account {account_id}: {e}",
                exc_info=True,
            )
            results.append(
                {
                    "account_id": account_id,
                    "success": False,
                    "message": str(e),
                }
            )
        finally:
            # release 已在 run_all() 内完成
            pass

    return {
        "success": True,
        "results": results,
        "total": len(account_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
    }


@shared_task(bind=True, name="google_business.subscription_click_subscribe")
def subscription_click_subscribe_task(
    self,
    account_ids: list,
    user_id: int | None = None,
    browser_type: str | None = None,
):
    """
    点击订阅按钮任务
    """
    import asyncio

    from .services import browser_pool
    from .services.subscription_service import SubscriptionVerifyService
    from apps.integrations.browser_base import BrowserType

    logger.info(f"Starting click subscribe task for {len(account_ids)} accounts")

    bt = BrowserType(browser_type) if browser_type else None
    subscription_service = SubscriptionVerifyService()
    results = []

    per_account_timeout_s = 420

    for i, account_id in enumerate(account_ids):
        email_for_release = None
        try:
            account = GoogleAccount.objects.get(id=account_id)
            email_for_release = account.email

            task_logger = TaskLogger(
                None,
                celery_task_id=str(self.request.id),
                account_id=account_id,
                email=account.email,
                kind="subscription_click_subscribe",
            )
            task_logger.event(
                step="task",
                action="start",
                message="start subscription_click_subscribe",
            )

            try:
                password = EncryptionUtil.decrypt(account.password)
            except Exception:
                password = account.password

            try:
                totp_secret = (
                    EncryptionUtil.decrypt(account.two_fa_secret)
                    if account.two_fa_secret
                    else ""
                )
            except Exception:
                totp_secret = account.two_fa_secret or ""

            account_info = {
                "email": account.email,
                "password": password,
                "totp_secret": totp_secret,
            }

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i + 1,
                    "total": len(account_ids),
                    "email": account.email,
                },
            )

            # 重要：Playwright 对象绑定 event loop，必须在同一 asyncio.run() 生命周期内
            # 完成 acquire -> login -> action -> release，避免跨 loop 使用导致挂死。
            async def run_all():
                instance = await browser_pool.acquire_by_email(
                    email=account.email,
                    task_id=str(self.request.id),
                    account_info=account_info,
                    browser_type=bt,
                )
                if not instance or not instance.page:
                    task_logger.event(
                        step="browser",
                        action="acquire",
                        level="error",
                        message="failed to acquire browser instance",
                    )
                    return False, "无法获取浏览器实例", None, None

                try:
                    attach_playwright_trace(instance.page, task_logger)

                    login_service = GoogleLoginService()
                    try:
                        logged_in = await login_service.check_login_status(
                            instance.page
                        )
                    except Exception:
                        logged_in = False

                    if not logged_in:
                        task_logger.event(
                            step="login",
                            action="start",
                            message="start login",
                            url=getattr(instance.page, "url", ""),
                        )
                        login_res = await login_service.login(
                            instance.page,
                            {
                                "email": account.email,
                                "password": password,
                                "secret": totp_secret,
                                "backup": account.recovery_email or "",
                            },
                            task_logger,
                        )
                        if not login_res.get("success"):
                            err = (
                                login_res.get("error") or login_res.get("message") or ""
                            )
                            task_logger.event(
                                step="login",
                                action="result",
                                level="error",
                                message="login failed",
                                url=getattr(instance.page, "url", ""),
                                result={"error": err},
                            )
                            return False, f"登录失败: {err}", None, None

                        task_logger.event(
                            step="login",
                            action="result",
                            message="login ok",
                            url=getattr(instance.page, "url", ""),
                        )

                    ok, msg = await subscription_service.click_subscribe_button(
                        instance.page,
                        account_info,
                    )
                    if ok:
                        (
                            _,
                            final_status,
                            screenshot,
                        ) = await subscription_service.verify_result(
                            instance.page,
                            account_info,
                        )
                        return ok, msg, final_status, screenshot
                    return ok, msg, None, None
                finally:
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(
                                browser_pool.release_by_email(
                                    account.email,
                                    browser_type=bt,
                                    close=True,
                                )
                            ),
                            timeout=30,
                        )
                    except Exception:
                        logger.warning(
                            "Failed to release browser instance (subscription click)",
                            exc_info=True,
                        )

            async def run_with_timeout():
                return await asyncio.wait_for(run_all(), timeout=per_account_timeout_s)

            try:
                ok, msg, final_status, screenshot = asyncio.run(run_with_timeout())
            except asyncio.TimeoutError:
                ok, msg, final_status, screenshot = False, "任务超时", None, None

            trace_file = task_logger.trace_rel_path or (
                str(task_logger.trace_file) if task_logger.trace_file else ""
            )
            task_logger.event(
                step="task",
                action="result",
                message="subscription_click_subscribe finished",
                level="info" if ok else "error",
                result={
                    "success": ok,
                    "message": msg,
                    "final_status": final_status,
                    "screenshot": screenshot or "",
                    "trace_file": trace_file,
                },
            )

            if ok and final_status:
                meta = account.metadata or {}
                meta["google_one_status"] = final_status
                if screenshot:
                    meta["google_one_screenshot"] = screenshot
                account.metadata = meta

                update_fields = ["metadata"]
                if final_status == "subscribed":
                    account.gemini_status = "active"
                    update_fields.append("gemini_status")
                if final_status == "verified":
                    account.sheerid_verified = True
                    update_fields.append("sheerid_verified")
                account.save(update_fields=list(set(update_fields)))

            results.append(
                {
                    "email": account.email,
                    "success": ok,
                    "message": msg,
                    "final_status": final_status,
                    "screenshot": screenshot,
                    "trace_file": trace_file,
                }
            )

        except Exception as e:
            logger.error(
                f"Click subscribe failed for account {account_id}: {e}", exc_info=True
            )
            results.append(
                {
                    "account_id": account_id,
                    "success": False,
                    "message": str(e),
                }
            )
        finally:
            # release 已在 run_all() 内完成
            pass

    return {
        "success": True,
        "results": results,
        "total": len(account_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
    }
