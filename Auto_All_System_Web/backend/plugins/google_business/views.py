"""
Google Business插件API视图
实现所有RESTful API端点
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
import logging

from apps.integrations.google_accounts.models import GoogleAccount
from .models import GoogleTask, GoogleCardInfo, GoogleTaskAccount, GoogleBusinessConfig
from .serializers import (
    GoogleAccountSerializer,
    GoogleAccountCreateSerializer,
    GoogleAccountImportSerializer,
    GoogleCardInfoSerializer,
    GoogleCardInfoCreateSerializer,
    GoogleCardInfoImportSerializer,
    GoogleTaskSerializer,
    GoogleTaskCreateSerializer,
    GoogleTaskAccountSerializer,
    GoogleBusinessConfigSerializer,
    StatisticsSerializer,
    PricingInfoSerializer,
)
from .utils import EncryptionUtil, calculate_task_cost

logger = logging.getLogger(__name__)


# ==================== 账号管理 ====================


class GoogleAccountViewSet(viewsets.ModelViewSet):
    """
    Google账号管理ViewSet

    提供以下端点：
    - GET /accounts/ - 获取账号列表
    - POST /accounts/ - 创建单个账号
    - GET /accounts/{id}/ - 获取账号详情
    - PUT /accounts/{id}/ - 更新账号信息
    - DELETE /accounts/{id}/ - 删除账号
    - POST /accounts/import/ - 批量导入账号
    - POST /accounts/bulk-delete/ - 批量删除账号
    - POST /accounts/export/ - 导出账号
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoogleAccountSerializer
    pagination_class = None  # 禁用分页，直接返回数组

    def get_queryset(self):
        """只返回当前用户的账号"""
        queryset = GoogleAccount.objects.filter(owner_user=self.request.user)

        # 过滤状态
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # 搜索邮箱
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(email__icontains=search)

        return queryset.order_by("-created_at")

    def create(self, request):
        """创建单个账号"""
        serializer = GoogleAccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # 检查邮箱是否已存在
        if GoogleAccount.objects.filter(email=data["email"]).exists():
            return Response(
                {"error": "该邮箱已存在"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 加密敏感数据
        account = GoogleAccount.objects.create(
            owner_user=request.user,
            email=data["email"],
            password=EncryptionUtil.encrypt(data["password"]),
            recovery_email=data.get("recovery_email", ""),
            notes=data.get("notes", ""),
        )

        return Response(
            GoogleAccountSerializer(account).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"])
    def import_accounts(self, request):
        """
        批量导入账号

        POST /api/v1/plugins/google-business/accounts/import/
        {
            "accounts": [
                "user1@gmail.com----pass1----backup1@gmail.com----SECRET1",
                "user2@gmail.com----pass2----backup2@gmail.com----SECRET2"
            ],
            "format": "email----password----recovery----secret",
            "match_browser": true,
            "overwrite_existing": false
        }
        """
        serializer = GoogleAccountImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accounts_data = serializer.validated_data["accounts"]
        match_browser = serializer.validated_data["match_browser"]
        overwrite_existing = serializer.validated_data["overwrite_existing"]

        imported_count = 0
        skipped_count = 0
        errors = []
        accounts_list = []

        # 如果需要匹配浏览器，获取所有浏览器窗口
        browser_map = {}
        if match_browser:
            try:
                from create_window import get_browser_list

                browsers = get_browser_list(page=0, pageSize=1000)
                for browser in browsers:
                    remark = browser.get("remark", "")
                    if "----" in remark:
                        parts = remark.split("----")
                        if parts and "@" in parts[0]:
                            browser_email = parts[0].strip()
                            browser_map[browser_email] = browser.get("id", "")
            except Exception as e:
                logger.error(f"Failed to fetch browser list: {e}")

        for line in accounts_data:
            try:
                parts = line.split("----")
                if len(parts) < 2:
                    errors.append(f"Invalid format: {line}")
                    continue

                email = parts[0].strip()
                password = parts[1].strip()
                recovery = parts[2].strip() if len(parts) > 2 else ""
                secret = parts[3].strip() if len(parts) > 3 else ""

                # 检查是否已存在
                existing = GoogleAccount.objects.filter(email=email).first()
                if existing:
                    if overwrite_existing:
                        # 更新
                        existing.password = EncryptionUtil.encrypt(password)
                        existing.recovery_email = recovery
                        existing.save()
                        accounts_list.append(existing)
                        imported_count += 1
                    else:
                        skipped_count += 1
                        continue
                else:
                    # 创建新账号
                    account = GoogleAccount.objects.create(
                        owner_user=request.user,
                        email=email,
                        password=EncryptionUtil.encrypt(password),
                        recovery_email=recovery,
                    )
                    accounts_list.append(account)
                    imported_count += 1

            except Exception as e:
                errors.append(f"Error processing {line}: {str(e)}")
                logger.error(f"Import account error: {e}", exc_info=True)

        return Response(
            {
                "success": True,
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "errors": errors,
                "accounts": GoogleAccountSerializer(accounts_list, many=True).data,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """
        批量删除账号

        POST /api/v1/plugins/google-business/accounts/bulk-delete/
        {
            "ids": [1, 2, 3]
        }
        """
        ids = request.data.get("ids", [])
        if not ids:
            return Response(
                {"error": "请提供要删除的账号ID"}, status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count = GoogleAccount.objects.filter(
            id__in=ids, owner_user=request.user
        ).delete()[0]

        return Response({"success": True, "deleted_count": deleted_count})

    @action(detail=False, methods=["post"])
    def export(self, request):
        """
        导出账号（敏感信息脱敏）

        POST /api/v1/plugins/google-business/accounts/export/
        """
        queryset = self.get_queryset()
        accounts = GoogleAccountSerializer(queryset, many=True).data

        return Response({"success": True, "count": len(accounts), "accounts": accounts})


# ==================== 卡信息管理 ====================
from apps.cards.models import Card
from apps.cards.serializers import CardSerializer, CardImportSerializer
from apps.cards.views import CardViewSet


class GoogleCardInfoViewSet(CardViewSet):
    """
    卡信息管理ViewSet (已对接统一的虚拟卡管理系统)
    """

    queryset = Card.objects.all()
    serializer_class = CardSerializer

    def get_queryset(self):
        """
        权限控制：
        1. 超级管理员可以看到所有卡
        2. 普通管理员/用户只能看到公共卡池的卡和自己的私有卡
        """
        user = self.request.user

        # 超级管理员能看到所有卡
        if user.is_superuser:
            return Card.objects.all().select_related("owner_user")

        # 普通用户/普通管理员：公共卡池 + 自己的私有卡
        return (
            Card.objects.filter(Q(owner_user=user) | Q(pool_type="public"))
            .select_related("owner_user")
            .order_by("-created_at")
        )

    @action(detail=False, methods=["post"])
    def import_cards(self, request):
        """批量导入虚拟卡 (对接统一接口)"""
        # 为了兼容前端插件端的传参格式
        data = request.data.copy()
        if "cards" in data and "cards_data" not in data:
            data["cards_data"] = data["cards"]

        # 默认导入为私有卡，因为这是在插件端（用户个人操作）
        if "pool_type" not in data:
            data["pool_type"] = "private"

        request._full_data = data  # 兼容 rest_framework
        return super().import_cards(request)


# ==================== 任务管理 ====================


class GoogleTaskViewSet(viewsets.ModelViewSet):
    """
    任务管理ViewSet

    提供以下端点：
    - GET /tasks/ - 获取任务列表
    - POST /tasks/ - 创建任务
    - GET /tasks/{id}/ - 获取任务详情
    - POST /tasks/{id}/cancel/ - 取消任务
    - POST /tasks/{id}/pause/ - 暂停任务
    - POST /tasks/{id}/resume/ - 恢复任务
    - POST /tasks/{id}/retry/ - 重试失败项
    - GET /tasks/{id}/log/ - 获取任务日志
    - GET /tasks/{id}/accounts/ - 获取任务的账号列表
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GoogleTaskSerializer

    def get_queryset(self):
        """只返回当前用户的任务"""
        queryset = GoogleTask.objects.filter(user=self.request.user)

        # 过滤任务类型
        task_type = self.request.query_params.get("task_type")
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        # 过滤状态
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by("-created_at")

    def create(self, request):
        """
        创建任务

        POST /api/v1/plugins/google-business/tasks/
        {
            "task_type": "one_click",
            "account_ids": [1, 2, 3],
            "config": {
                "max_concurrency": 3,
                "delays": {"after_offer": 8, "after_add_card": 10, "after_save": 18},
                "sheerid_api_key": "xxx"
            }
        }
        """
        serializer = GoogleTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_type = serializer.validated_data["task_type"]
        account_ids = serializer.validated_data["account_ids"]
        config = serializer.validated_data.get("config", {})

        # 验证账号是否属于当前用户
        accounts = GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        )

        if accounts.count() != len(account_ids):
            return Response(
                {"error": "部分账号不存在或无权限"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 估算费用
        estimated_cost = calculate_task_cost(task_type, len(account_ids))

        # 检查余额
        balance_obj = getattr(request.user, "balance", None)
        if balance_obj is None:
            from apps.accounts.models import UserBalance

            balance_obj = UserBalance.objects.create(user=request.user, balance=0)

        available_balance = float(balance_obj.available_balance)
        if available_balance < estimated_cost:
            return Response(
                {
                    "error": "积分不足",
                    "required": estimated_cost,
                    "balance": available_balance,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 创建任务
        task = GoogleTask.objects.create(
            user=request.user,
            task_type=task_type,
            total_count=len(account_ids),
            estimated_cost=estimated_cost,
            config=config,
            status="pending",
        )

        # 创建任务-账号关联
        task_accounts = [
            GoogleTaskAccount(task=task, account=account) for account in accounts
        ]
        GoogleTaskAccount.objects.bulk_create(task_accounts)

        # 提交Celery异步任务
        from .tasks import batch_process_task

        account_id_list = list(accounts.values_list("id", flat=True))
        celery_task = batch_process_task.delay(
            task.id, account_id_list, task_type, config
        )
        task.celery_task_id = celery_task.id
        task.status = "running"
        task.started_at = timezone.now()
        task.save()

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "estimated_cost": estimated_cost,
                "message": "任务已创建并开始执行",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """取消任务"""
        task = self.get_object()

        if task.status not in ["pending", "running", "paused"]:
            return Response(
                {"error": "任务状态不允许取消"}, status=status.HTTP_400_BAD_REQUEST
            )

        task.status = "cancelled"
        task.completed_at = timezone.now()
        task.save()

        # TODO: 取消Celery任务

        return Response({"success": True, "message": "任务已取消"})

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """暂停任务"""
        task = self.get_object()

        if task.status != "running":
            return Response(
                {"error": "只能暂停运行中的任务"}, status=status.HTTP_400_BAD_REQUEST
            )

        task.status = "paused"
        task.save()

        # TODO: 暂停Celery任务

        return Response({"success": True, "message": "任务已暂停"})

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """恢复任务"""
        task = self.get_object()

        if task.status != "paused":
            return Response(
                {"error": "只能恢复已暂停的任务"}, status=status.HTTP_400_BAD_REQUEST
            )

        task.status = "running"
        task.save()

        # TODO: 恢复Celery任务

        return Response({"success": True, "message": "任务已恢复"})

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """重试失败项"""
        task = self.get_object()

        # 获取失败的账号
        failed_accounts = GoogleTaskAccount.objects.filter(
            task=task, status="failed"
        ).values_list("account_id", flat=True)

        if not failed_accounts:
            return Response(
                {"error": "没有失败的账号需要重试"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 创建新任务
        new_task = GoogleTask.objects.create(
            user=task.user,
            task_type=task.task_type,
            total_count=len(failed_accounts),
            estimated_cost=calculate_task_cost(task.task_type, len(failed_accounts)),
            config=task.config,
            status="pending",
        )

        # 创建任务-账号关联
        task_accounts = [
            GoogleTaskAccount(task=new_task, account_id=account_id)
            for account_id in failed_accounts
        ]
        GoogleTaskAccount.objects.bulk_create(task_accounts)

        return Response(
            {
                "success": True,
                "new_task_id": new_task.id,
                "retry_count": len(failed_accounts),
                "message": f"已创建重试任务 #{new_task.id}",
            }
        )

    @action(detail=True, methods=["get"])
    def log(self, request, pk=None):
        """获取任务日志"""
        task = self.get_object()

        return Response({"task_id": task.id, "log": task.log})

    @action(detail=True, methods=["get"])
    def accounts(self, request, pk=None):
        """获取任务的账号列表"""
        task = self.get_object()

        task_accounts = GoogleTaskAccount.objects.filter(task=task)
        serializer = GoogleTaskAccountSerializer(task_accounts, many=True)

        return Response(
            {
                "task_id": task.id,
                "total": task_accounts.count(),
                "accounts": serializer.data,
            }
        )


# ==================== 统计和配置 ====================


class StatisticsView(viewsets.ViewSet):
    """统计数据API"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """
        获取概览统计

        GET /api/v1/plugins/google-business/statistics/overview/
        """
        user = request.user

        # 账号统计（按用户归属）
        # GoogleAccount 模型使用 owner_user 字段关联所属用户。
        accounts = GoogleAccount.objects.filter(owner_user=user)

        # 状态值在不同模块/迁移版本里可能存在差异，这里做兼容统计。
        stats = {
            "total": accounts.count(),
            # pending: 兼容 pending_check
            "pending": accounts.filter(status__in=["pending", "pending_check"]).count(),
            "logged_in": accounts.filter(status="logged_in").count(),
            "link_ready": accounts.filter(status="link_ready").count(),
            "verified": accounts.filter(status="verified").count(),
            "subscribed": accounts.filter(status="subscribed").count(),
            "ineligible": accounts.filter(status="ineligible").count(),
            "error": accounts.filter(status="error").count(),
        }

        serializer = StatisticsSerializer(data=stats)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pricing(self, request):
        """
        获取定价信息

        GET /api/v1/plugins/google-business/statistics/pricing/
        """
        pricing = {
            "login": 1,
            "get_link": 2,
            "verify": 5,
            "bind_card": 10,
            "one_click": 18,
        }

        serializer = PricingInfoSerializer(data=pricing)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


class SettingsViewSet(viewsets.ViewSet):
    """设置API"""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        获取设置

        GET /api/v1/plugins/google-business/settings/
        """
        config = GoogleBusinessConfig.objects.filter(key="default").first()
        if not config:
            return Response(
                {
                    "sheerid_enabled": True,
                    "gemini_enabled": True,
                    "auto_verify": False,
                    "settings": {},
                }
            )

        serializer = GoogleBusinessConfigSerializer(config)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """
        更新设置

        PUT /api/v1/plugins/google-business/settings/{key}/
        """
        config, created = GoogleBusinessConfig.objects.get_or_create(key="default")

        serializer = GoogleBusinessConfigSerializer(
            config, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


# ==================== 浏览器管理 ====================


class BrowserManagementViewSet(viewsets.ViewSet):
    """
    浏览器管理API

    提供多浏览器类型支持（比特浏览器 / GeekezBrowser）
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def available(self, request):
        """
        获取可用的浏览器列表

        GET /api/v1/plugins/google-business/browser/available/
        """
        from apps.integrations.browser_base import get_browser_manager

        manager = get_browser_manager()
        browsers = manager.list_available()

        return Response(
            {
                "browsers": browsers,
                "default": manager._default_type.value,
            }
        )

    @action(detail=False, methods=["post"])
    def set_default(self, request):
        """
        设置默认浏览器类型

        POST /api/v1/plugins/google-business/browser/set_default/
        """
        from apps.integrations.browser_base import get_browser_manager, BrowserType

        browser_type = request.data.get("browser_type")

        try:
            bt = BrowserType(browser_type)
            manager = get_browser_manager()
            manager.set_default(bt)

            return Response(
                {
                    "success": True,
                    "default": bt.value,
                }
            )
        except ValueError:
            return Response(
                {"error": f"无效的浏览器类型: {browser_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"])
    def pool_stats(self, request):
        """
        获取浏览器资源池统计

        GET /api/v1/plugins/google-business/browser/pool_stats/
        """
        from .services import browser_pool

        stats = browser_pool.get_pool_stats()
        return Response(stats)

    @action(detail=False, methods=["get"])
    def status(self, request):
        """
        获取当前浏览器连接状态（用于前端展示/自检）

        GET /api/v1/plugins/google-business/browser/status/

        Returns:
            {
              "default": "geekez",
              "engine_online": true,
              "pool_connected": false,
              "pool": {"total": 0, "busy": 0, "idle": 0, "max_size": 10},
              "browsers": [{"type": "geekez", "online": true, "is_default": true}, ...]
            }
        """
        from apps.integrations.browser_base import get_browser_manager
        from .services import browser_pool

        manager = get_browser_manager()
        default_type = manager._default_type

        try:
            engine_online = manager.health_check(default_type)
        except Exception:
            engine_online = False

        pool_stats = browser_pool.get_pool_stats()

        return Response(
            {
                "default": default_type.value,
                "engine_online": engine_online,
                "pool_connected": bool(pool_stats.get("total", 0) > 0),
                "pool": {
                    "total": pool_stats.get("total", 0),
                    "busy": pool_stats.get("busy", 0),
                    "idle": pool_stats.get("idle", 0),
                    "max_size": pool_stats.get("max_size", 0),
                },
                "browsers": manager.list_available(),
            }
        )


# ==================== 安全设置 ====================


class SecurityViewSet(viewsets.ViewSet):
    """
    安全设置API

    提供 2FA 修改、辅助邮箱修改、备份码获取等功能
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def change_2fa(self, request):
        """
        修改 2FA 密钥

        POST /api/v1/plugins/google-business/security/change_2fa/
        {
            "account_ids": [1, 2, 3],
            "browser_type": "bitbrowser"  // 可选
        }
        """
        account_ids = request.data.get("account_ids", [])
        # browser_type 可选；默认走系统默认浏览器（当前优先 GeekezBrowser）
        from apps.integrations.browser_base import get_browser_manager

        browser_type = (
            request.data.get("browser_type")
            or get_browser_manager()._default_type.value
        )

        if not account_ids:
            return Response({"error": "请选择账号"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建异步任务
        from .tasks import security_change_2fa_task

        task = security_change_2fa_task.delay(
            account_ids=account_ids,
            user_id=request.user.id,
            browser_type=browser_type,
        )

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "message": "2FA 修改任务已提交",
            }
        )

    @action(detail=False, methods=["post"])
    def change_recovery_email(self, request):
        """
        修改辅助邮箱

        POST /api/v1/plugins/google-business/security/change_recovery_email/
        {
            "account_ids": [1, 2, 3],
            "new_email": "new@example.com",
            "browser_type": "bitbrowser"
        }
        """
        account_ids = request.data.get("account_ids", [])
        new_email = request.data.get("new_email")
        from apps.integrations.browser_base import get_browser_manager

        browser_type = (
            request.data.get("browser_type")
            or get_browser_manager()._default_type.value
        )

        if not account_ids:
            return Response({"error": "请选择账号"}, status=status.HTTP_400_BAD_REQUEST)

        if not new_email:
            return Response(
                {"error": "请输入新的辅助邮箱"}, status=status.HTTP_400_BAD_REQUEST
            )

        from .tasks import security_change_recovery_email_task

        task = security_change_recovery_email_task.delay(
            account_ids=account_ids,
            new_email=new_email,
            user_id=request.user.id,
            browser_type=browser_type,
        )

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "message": "辅助邮箱修改任务已提交",
            }
        )

    @action(detail=False, methods=["post"])
    def get_backup_codes(self, request):
        """
        获取备份验证码

        POST /api/v1/plugins/google-business/security/get_backup_codes/
        {
            "account_ids": [1, 2, 3],
            "browser_type": "bitbrowser"
        }
        """
        account_ids = request.data.get("account_ids", [])
        from apps.integrations.browser_base import get_browser_manager

        browser_type = (
            request.data.get("browser_type")
            or get_browser_manager()._default_type.value
        )

        if not account_ids:
            return Response({"error": "请选择账号"}, status=status.HTTP_400_BAD_REQUEST)

        from .tasks import security_get_backup_codes_task

        task = security_get_backup_codes_task.delay(
            account_ids=account_ids,
            user_id=request.user.id,
            browser_type=browser_type,
        )

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "message": "备份码获取任务已提交",
            }
        )

    @action(detail=False, methods=["post"])
    def one_click_update(self, request):
        """
        一键修改全部安全设置

        POST /api/v1/plugins/google-business/security/one_click_update/
        {
            "account_ids": [1, 2, 3],
            "new_recovery_email": "new@example.com",  // 可选
            "browser_type": "bitbrowser"
        }
        """
        account_ids = request.data.get("account_ids", [])
        new_recovery_email = request.data.get("new_recovery_email")
        from apps.integrations.browser_base import get_browser_manager

        browser_type = (
            request.data.get("browser_type")
            or get_browser_manager()._default_type.value
        )

        if not account_ids:
            return Response({"error": "请选择账号"}, status=status.HTTP_400_BAD_REQUEST)

        from .tasks import security_one_click_task

        task = security_one_click_task.delay(
            account_ids=account_ids,
            new_recovery_email=new_recovery_email,
            user_id=request.user.id,
            browser_type=browser_type,
        )

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "message": "一键安全设置任务已提交",
            }
        )


# ==================== 订阅验证 ====================


class SubscriptionViewSet(viewsets.ViewSet):
    """
    订阅验证API

    提供订阅状态检测、截图、点击订阅等功能
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def verify_status(self, request):
        """
        验证订阅状态

        POST /api/v1/plugins/google-business/subscription/verify_status/
        {
            "account_ids": [1, 2, 3],
            "take_screenshot": true,
            "browser_type": "bitbrowser"
        }
        """
        account_ids = request.data.get("account_ids", [])
        take_screenshot = request.data.get("take_screenshot", True)
        from apps.integrations.browser_base import get_browser_manager

        browser_type = (
            request.data.get("browser_type")
            or get_browser_manager()._default_type.value
        )

        if not account_ids:
            return Response({"error": "请选择账号"}, status=status.HTTP_400_BAD_REQUEST)

        from .tasks import subscription_verify_status_task

        task = subscription_verify_status_task.delay(
            account_ids=account_ids,
            take_screenshot=take_screenshot,
            user_id=request.user.id,
            browser_type=browser_type,
        )

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "message": "订阅状态验证任务已提交",
            }
        )

    @action(detail=False, methods=["post"])
    def click_subscribe(self, request):
        """
        点击订阅按钮

        POST /api/v1/plugins/google-business/subscription/click_subscribe/
        {
            "account_ids": [1, 2, 3],
            "browser_type": "bitbrowser"
        }
        """
        account_ids = request.data.get("account_ids", [])
        from apps.integrations.browser_base import get_browser_manager

        browser_type = (
            request.data.get("browser_type")
            or get_browser_manager()._default_type.value
        )

        if not account_ids:
            return Response({"error": "请选择账号"}, status=status.HTTP_400_BAD_REQUEST)

        from .tasks import subscription_click_subscribe_task

        task = subscription_click_subscribe_task.delay(
            account_ids=account_ids,
            user_id=request.user.id,
            browser_type=browser_type,
        )

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "message": "点击订阅任务已提交",
            }
        )
