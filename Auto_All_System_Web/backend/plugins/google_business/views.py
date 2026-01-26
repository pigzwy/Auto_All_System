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
from django.http import FileResponse
from django.conf import settings
from pathlib import Path
import os
import logging

from apps.integrations.google_accounts.models import GoogleAccount, AccountGroup
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
    AccountGroupSerializer,
    AccountGroupCreateSerializer,
)
from .utils import EncryptionUtil, calculate_task_cost

logger = logging.getLogger(__name__)


class CeleryTaskViewSet(viewsets.ViewSet):
    """Celery 任务状态查询（用于前端轮询）。

    说明：Security / Subscription 相关接口目前返回的是 celery task_id（不是 GoogleTask 主表 id）。
    这里提供一个统一的查询入口，让前端不再用 setTimeout 模拟。
    """

    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        from celery.result import AsyncResult

        if not pk:
            return Response(
                {"error": "task_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        res = AsyncResult(pk)
        state = res.state

        payload: dict = {
            "task_id": pk,
            "state": state,
        }

        # res.info 在不同 state 下类型不同：
        # - PROGRESS: 通常为 dict meta
        # - FAILURE: 通常为 Exception
        # - SUCCESS: result 在 res.result
        if state == "PROGRESS":
            info = res.info
            payload["meta"] = info if isinstance(info, dict) else {"info": str(info)}
        elif state == "SUCCESS":
            payload["result"] = res.result
        elif state == "FAILURE":
            payload["error"] = str(res.result)
            # traceback 可能较长，必要时前端只展示 error 即可
            payload["traceback"] = res.traceback

        return Response(payload)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        from celery.result import AsyncResult

        if not pk:
            return Response(
                {"error": "task_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        AsyncResult(pk).revoke(terminate=False)
        return Response({"success": True, "task_id": pk})

    @action(detail=True, methods=["get"], url_path="trace")
    def trace(self, request, pk=None):
        """读取某个 celery task + 某个账号的 trace 日志（用于前端滚动/轮询）。

        Query Params:
        - email: 账号邮箱（推荐）
        - account_id: 账号ID（可选，优先级低于 email）
        - direction: forward | backward
          - backward: 向上翻历史（从 cursor 往前读）
          - forward: 追日志（从 cursor 往后读，适合轮询）
        - cursor: 文件字节偏移（int）。
          - backward: cursor 默认文件末尾
          - forward: cursor 默认 0
        - limit_bytes: 单次读取最大字节数，默认 262144（256KB）

        Response:
        - trace_file: 相对路径 logs/trace/...
        - cursor_in / cursor_out / has_more
        - lines: 文本行数组（包含 json line + human line）
        """

        if not pk:
            return Response(
                {"error": "task_id required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 1) 鉴权：必须确认 email/account 属于当前用户
        email = (request.query_params.get("email") or "").strip()
        account_id = (request.query_params.get("account_id") or "").strip()
        account: GoogleAccount | None = None
        if email:
            account = GoogleAccount.objects.filter(
                owner_user=request.user, email=email
            ).first()
        elif account_id:
            try:
                account = GoogleAccount.objects.filter(
                    owner_user=request.user, id=int(account_id)
                ).first()
            except Exception:
                account = None

        if not account:
            return Response(
                {"error": "account not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # 2) 解析读取参数
        direction = (request.query_params.get("direction") or "backward").strip()
        if direction not in ("backward", "forward"):
            direction = "backward"

        try:
            limit_bytes = int(request.query_params.get("limit_bytes") or 262144)
        except Exception:
            limit_bytes = 262144
        limit_bytes = max(4096, min(limit_bytes, 1024 * 1024))  # 4KB - 1MB

        cursor_raw = request.query_params.get("cursor")
        cursor_in: int | None
        try:
            cursor_in = int(cursor_raw) if cursor_raw is not None else None
        except Exception:
            cursor_in = None

        # 3) 定位 trace 文件（与 TaskLogger 的命名规则保持一致）
        safe_email = (account.email or "").replace("@", "_").replace(".", "_")
        trace_rel = str(Path("logs") / "trace" / f"trace_{pk}_{safe_email}.log")

        base_dir = Path(getattr(settings, "BASE_DIR", "."))
        trace_dir = (base_dir / "logs" / "trace").resolve()
        abs_path = (base_dir / trace_rel).resolve()

        # 防路径穿越
        try:
            abs_path.relative_to(trace_dir)
        except Exception:
            return Response(
                {"error": "invalid trace path"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not abs_path.exists() or not abs_path.is_file():
            return Response(
                {
                    "error": "trace file not found",
                    "trace_file": trace_rel,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # 4) 读取（byte offset）
        size = os.path.getsize(abs_path)

        if direction == "backward":
            end = size if cursor_in is None else max(0, min(cursor_in, size))
            start = max(0, end - limit_bytes)
            with open(abs_path, "rb") as f:
                f.seek(start)
                data = f.read(end - start)
            # 为避免截断第一行（partial line），backward 模式丢弃第一行的残片
            text = data.decode("utf-8", errors="ignore")
            lines = text.splitlines()
            if start > 0 and lines:
                lines = lines[1:]
            cursor_out = start
            has_more = start > 0
        else:
            start = 0 if cursor_in is None else max(0, min(cursor_in, size))
            end = min(size, start + limit_bytes)
            with open(abs_path, "rb") as f:
                f.seek(start)
                data = f.read(end - start)
            text = data.decode("utf-8", errors="ignore")
            lines = text.splitlines()
            cursor_out = end
            has_more = end < size

        # 限制最大行数，避免极端情况下返回过大
        if len(lines) > 5000:
            lines = lines[-5000:] if direction == "backward" else lines[:5000]

        return Response(
            {
                "task_id": pk,
                "email": account.email,
                "direction": direction,
                "trace_file": trace_rel,
                "cursor_in": cursor_in,
                "cursor_out": cursor_out,
                "has_more": has_more,
                "size": size,
                "lines": lines,
            }
        )


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

    def list(self, request, *args, **kwargs):
        """账号列表。

        额外注入 geekez_profile_names，用于前端展示“Geek 环境是否存在”。
        为避免每个账号都单独读取 profiles.json，这里只读一次。
        """

        queryset = self.filter_queryset(self.get_queryset())

        geekez_names = set()
        try:
            from apps.integrations.browser_base import get_browser_manager, BrowserType

            manager = get_browser_manager()
            api = manager.get_api(BrowserType.GEEKEZ)
            # list_profiles 会读取本地 profiles.json（或挂载目录），只调用一次
            geekez_names = {
                p.name for p in api.list_profiles() if getattr(p, "name", None)
            }
        except Exception:
            geekez_names = set()

        context = self.get_serializer_context()
        context["geekez_profile_names"] = geekez_names

        serializer = self.get_serializer(queryset, many=True, context=context)
        return Response(serializer.data)

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

        # 过滤分组
        group = self.request.query_params.get("group")
        if group:
            queryset = queryset.filter(group_id=group)

        # 过滤派生类型标签（前端展示用：无资格/未绑卡/成功）
        type_tag = self.request.query_params.get(
            "type_tag"
        ) or self.request.query_params.get("type")
        if type_tag:
            if type_tag == "ineligible":
                queryset = queryset.filter(
                    Q(metadata__google_one_status="ineligible") | Q(status="ineligible")
                )
            elif type_tag == "unbound_card":
                queryset = queryset.filter(
                    Q(card_bound=False)
                    & (
                        Q(sheerid_verified=True)
                        | Q(metadata__google_one_status="verified")
                        | Q(status="verified")
                    )
                )
            elif type_tag == "success":
                queryset = queryset.filter(
                    Q(gemini_status="active")
                    | Q(metadata__google_one_status="subscribed")
                    | Q(status="subscribed")
                )
            elif type_tag == "other":
                # other: 排除已知类型
                queryset = queryset.exclude(
                    Q(metadata__google_one_status="ineligible")
                    | Q(status="ineligible")
                    | (
                        Q(card_bound=False)
                        & (
                            Q(sheerid_verified=True)
                            | Q(metadata__google_one_status="verified")
                            | Q(status="verified")
                        )
                    )
                    | Q(gemini_status="active")
                    | Q(metadata__google_one_status="subscribed")
                    | Q(status="subscribed")
                )

        return queryset.order_by("-created_at")

    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        """获取单个账号关联的任务/日志概览。

        返回：
        - google_tasks: 通过 GoogleTaskAccount 关联到的 GoogleTask 列表（含进度/状态）
        - task_accounts: 该账号在每个任务中的执行状态与结果

        注：Security/Subscription 目前是 celery task_id 轮询，不在 GoogleTask 表里；
        如需展示，可从账号 metadata 中的 google_one_status/google_one_status_info/screenshot 等获取。
        """

        account = get_object_or_404(GoogleAccount, id=pk, owner_user=request.user)

        from .models import GoogleTaskAccount

        rels = (
            GoogleTaskAccount.objects.filter(account=account)
            .select_related("task")
            .order_by("-task__created_at")
        )

        import re

        step_titles = {
            1: "登录账号",
            2: "打开 Google One",
            3: "检查学生资格",
            4: "学生验证",
            5: "订阅服务",
            6: "完成处理",
        }

        def parse_main_flow(log_text: str):
            if not isinstance(log_text, str) or not log_text:
                return {"step_num": 0, "step_title": None, "extras": []}

            # 取最后一次出现的 "步骤 x/6:" 作为最近步骤
            last_num = 0
            for m in re.finditer(r"步骤\s*(\d+)\/6", log_text):
                try:
                    last_num = max(last_num, int(m.group(1)))
                except Exception:
                    continue

            extras: list[str] = []
            for m in re.finditer(r"增项:\s*([^\r\n]+)", log_text):
                val = (m.group(1) or "").strip()
                if val and val not in extras:
                    extras.append(val)

            return {
                "step_num": last_num,
                "step_title": step_titles.get(last_num),
                "extras": extras,
            }

        google_tasks = []
        task_accounts = []

        for rel in rels:
            task = rel.task

            main_flow = {
                "step_num": 0,
                "step_title": None,
                "extras": [],
            }
            if task.task_type == "one_click":
                try:
                    main_flow = parse_main_flow(task.log or "")
                except Exception:
                    main_flow = {
                        "step_num": 0,
                        "step_title": None,
                        "extras": [],
                    }

            google_tasks.append(
                {
                    "id": task.id,
                    "task_type": task.task_type,
                    "task_type_display": task.get_task_type_display(),
                    "status": task.status,
                    "status_display": task.get_status_display(),
                    "progress_percentage": task.progress_percentage,
                    "main_flow_step_num": main_flow.get("step_num"),
                    "main_flow_step_title": main_flow.get("step_title"),
                    "main_flow_extras": main_flow.get("extras"),
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                }
            )
            task_accounts.append(
                {
                    "task_id": task.id,
                    "status": rel.status,
                    "status_display": rel.get_status_display(),
                    "result_message": rel.result_message,
                    "error_message": rel.error_message,
                    "started_at": rel.started_at,
                    "completed_at": rel.completed_at,
                    "duration": rel.duration,
                }
            )

        meta = account.metadata or {}

        # 统一的“任务记录”列表：合并 GoogleTask 与 celery action。
        # - GoogleTask：有稳定的任务ID、进度、日志
        # - Celery action：返回 celery_task_id，细节从 celery-tasks/{id} 查询
        kind_display = {
            "security_change_2fa": "安全设置-修改2FA",
            "security_change_recovery_email": "安全设置-修改辅助邮箱",
            "security_get_backup_codes": "安全设置-获取备份码",
            "security_one_click": "安全设置-一键安全更新",
            "subscription_verify_status": "订阅-验证订阅状态",
            "subscription_click_subscribe": "订阅-点击订阅",
        }

        tasks = []

        for t in google_tasks:
            created_at = t.get("created_at")
            try:
                created_at_str = (
                    created_at.isoformat()
                    if hasattr(created_at, "isoformat")
                    else str(created_at)
                )
            except Exception:
                created_at_str = str(created_at)

            tasks.append(
                {
                    "record_id": f"google:{t.get('id')}",
                    "source": "google",
                    "google_task_id": t.get("id"),
                    "name": t.get("task_type_display") or t.get("task_type"),
                    "task_type": t.get("task_type"),
                    "status": t.get("status"),
                    "status_display": t.get("status_display") or t.get("status"),
                    "progress_percentage": t.get("progress_percentage"),
                    "main_flow_step_num": t.get("main_flow_step_num"),
                    "main_flow_step_title": t.get("main_flow_step_title"),
                    "main_flow_extras": t.get("main_flow_extras"),
                    "created_at": created_at_str,
                }
            )

        for a in meta.get("google_zone_actions") or []:
            if not isinstance(a, dict):
                continue
            created_at_str = str(a.get("created_at") or "")
            kind = a.get("kind")
            tasks.append(
                {
                    "record_id": f"celery:{a.get('celery_task_id')}",
                    "source": "celery",
                    "celery_task_id": a.get("celery_task_id"),
                    "name": kind_display.get(kind) or kind or "celery_task",
                    "kind": kind,
                    "state": a.get("state"),
                    "created_at": created_at_str,
                }
            )

        # 排序：按 created_at 倒序（created_at 为 ISO 字符串时可直接按解析结果排序）
        try:
            from django.utils.dateparse import parse_datetime

            def _key(item):
                dt = parse_datetime(item.get("created_at") or "")
                if dt is None:
                    return timezone.datetime.min.replace(tzinfo=timezone.utc)
                if timezone.is_naive(dt):
                    try:
                        return timezone.make_aware(dt, timezone.get_current_timezone())
                    except Exception:
                        return dt.replace(tzinfo=timezone.utc)
                return dt

            tasks.sort(key=_key, reverse=True)
        except Exception:
            # 兜底：按字符串排序
            tasks.sort(key=lambda x: (x.get("created_at") or ""), reverse=True)

        return Response(
            {
                "account_id": account.id,
                "email": account.email,
                "google_one_status": meta.get("google_one_status"),
                "google_one_status_info": meta.get("google_one_status_info"),
                "google_one_screenshot": meta.get("google_one_screenshot"),
                # 统一任务记录（推荐前端使用）
                "tasks": tasks,
                # 兼容旧字段（前端仍可能使用）
                "celery_actions": meta.get("google_zone_actions") or [],
                "google_tasks": google_tasks,
                "task_accounts": task_accounts,
            }
        )

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

    @action(detail=True, methods=["patch"])
    def edit(self, request, pk=None):
        """编辑账号（支持修改密码/2FA/恢复邮箱/备注）。

        PATCH /api/v1/plugins/google-business/accounts/{id}/edit/
        {
          "email": "optional",
          "password": "optional",
          "recovery_email": "optional",
          "secret_key": "optional",  # 2FA secret
          "notes": "optional"
        }
        """

        from .serializers import GoogleAccountEditSerializer

        account = get_object_or_404(GoogleAccount, id=pk, owner_user=request.user)
        serializer = GoogleAccountEditSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        update_fields = []

        # email
        if "email" in data and data["email"] and data["email"] != account.email:
            if (
                GoogleAccount.objects.filter(email=data["email"])
                .exclude(id=account.id)
                .exists()
            ):
                return Response(
                    {"error": "该邮箱已存在"}, status=status.HTTP_400_BAD_REQUEST
                )
            account.email = data["email"]
            update_fields.append("email")

        # password
        if "password" in data and data["password"] is not None:
            # 允许清空：空字符串表示不修改
            if str(data["password"]).strip():
                account.password = EncryptionUtil.encrypt(str(data["password"]))
                update_fields.append("password")

        # recovery_email
        if "recovery_email" in data:
            account.recovery_email = str(data.get("recovery_email") or "")
            update_fields.append("recovery_email")

        # 2FA secret
        if "secret_key" in data and data["secret_key"] is not None:
            secret = str(data.get("secret_key") or "")
            if secret.strip():
                account.two_fa_secret = EncryptionUtil.encrypt(secret)
                account.two_fa_enabled = True
                update_fields.extend(["two_fa_secret", "two_fa_enabled"])
            else:
                # 空字符串表示不修改（避免误把 2FA 清掉）
                pass

        # notes
        if "notes" in data:
            account.notes = str(data.get("notes") or "")
            update_fields.append("notes")

        if update_fields:
            account.save(update_fields=list(set(update_fields)))

        return Response(GoogleAccountSerializer(account).data)

    @action(detail=False, methods=["post"])
    def export_csv(self, request):
        """导出账号为 CSV（包含敏感字段：密码/2FA，会解密）。

        POST /api/v1/plugins/google-business/accounts/export_csv/
        {"ids": [1,2,3]}  # 可选，不传则导出当前用户全部
        """

        import csv
        import io
        from django.http import HttpResponse

        ids = request.data.get("ids")
        qs = GoogleAccount.objects.filter(owner_user=request.user)
        if isinstance(ids, list) and ids:
            qs = qs.filter(id__in=ids)

        buf = io.StringIO()
        writer = csv.writer(buf)
        # 英文表头避免编码兼容问题
        writer.writerow(
            [
                "email",
                "password",
                "recovery_email",
                "two_fa_secret",
                "status",
                "sheerid_verified",
                "gemini_status",
                "card_bound",
                "notes",
            ]
        )

        for a in qs.order_by("-created_at"):
            try:
                pwd = EncryptionUtil.decrypt(a.password)
            except Exception:
                pwd = a.password

            try:
                secret = (
                    EncryptionUtil.decrypt(a.two_fa_secret) if a.two_fa_secret else ""
                )
            except Exception:
                secret = a.two_fa_secret or ""

            writer.writerow(
                [
                    a.email,
                    pwd,
                    a.recovery_email or "",
                    secret,
                    a.status,
                    "1" if a.sheerid_verified else "0",
                    a.gemini_status,
                    "1" if a.card_bound else "0",
                    (a.notes or "").replace("\n", " ").replace("\r", " "),
                ]
            )

        content = buf.getvalue()
        resp = HttpResponse(content, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="google_accounts.csv"'
        return resp

    @action(detail=False, methods=["post"])
    def export_txt(self, request):
        """导出账号为 TXT（包含敏感字段：密码/2FA，会解密）。

        POST /api/v1/plugins/google-business/accounts/export_txt/
        {"ids": [1,2,3]}  # 可选，不传则导出当前用户全部

        每行格式：email----password----recovery_email----two_fa_secret
        """

        from django.http import HttpResponse

        ids = request.data.get("ids")
        qs = GoogleAccount.objects.filter(owner_user=request.user)
        if isinstance(ids, list) and ids:
            qs = qs.filter(id__in=ids)

        lines = []
        for a in qs.order_by("-created_at"):
            try:
                pwd = EncryptionUtil.decrypt(a.password)
            except Exception:
                pwd = a.password

            try:
                secret = (
                    EncryptionUtil.decrypt(a.two_fa_secret) if a.two_fa_secret else ""
                )
            except Exception:
                secret = a.two_fa_secret or ""

            recovery = a.recovery_email or ""
            lines.append(f"{a.email}----{pwd}----{recovery}----{secret}")

        content = "\n".join(lines)
        resp = HttpResponse(content, content_type="text/plain; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="google_accounts.txt"'
        return resp

    @action(detail=True, methods=["post"])
    def launch_geekez(self, request, pk=None):
        """创建/打开 GeekezBrowser 的账号环境。

        统一语义：
        - 若 Geekez 中不存在对应邮箱的 profile：创建环境（profile）后再打开。
        - 若已存在：直接打开（不再创建）。
        - 同时把 profile 信息与启动信息写入账号 metadata，便于后续在系统内展示/追踪。

        POST /api/v1/plugins/google-business/accounts/{id}/launch_geekez/

        Returns:
            {
              "success": true,
              "created_profile": true,
              "browser_type": "geekez",
              "profile_id": "...",
              "debug_port": 12345,
              "cdp_endpoint": "http://...",
              "ws_endpoint": "ws://...",
              "pid": 1234,
              "saved": true
            }
        """

        from apps.integrations.browser_base import get_browser_manager, BrowserType

        account = get_object_or_404(GoogleAccount, id=pk, owner_user=request.user)

        manager = get_browser_manager()
        try:
            api = manager.get_api(BrowserType.GEEKEZ)
        except Exception:
            return Response(
                {"error": "GeekezBrowser 未配置或不可用"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not api.health_check():
            return Response(
                {"error": "GeekezBrowser 服务不在线"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 优先复用已有 profile（避免“重复创建环境”）
        created_profile = False
        profile = api.get_profile_by_name(account.email)
        if not profile:
            created_profile = True
            # 创建 profile。不要写入明文敏感信息到 profile metadata。
            profile = api.create_or_update_profile(
                name=account.email,
                proxy=None,
                metadata={"account": {"email": account.email}},
            )

        launch_info = api.launch_profile(profile.id)
        if not launch_info:
            return Response(
                {"error": "启动 Geekez profile 失败"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        meta = account.metadata or {}
        # 持久化“环境已创建”的信息（即使浏览器没开着，也能知道 profile 已存在）
        meta["geekez_profile"] = {
            "browser_type": BrowserType.GEEKEZ.value,
            "profile_id": profile.id,
            "profile_name": profile.name,
            "created_by_system": True,
            "created_at": (meta.get("geekez_profile") or {}).get("created_at")
            or timezone.now().isoformat(),
        }
        meta["geekez_env"] = {
            "browser_type": BrowserType.GEEKEZ.value,
            "profile_id": launch_info.profile_id,
            "debug_port": launch_info.debug_port,
            "cdp_endpoint": launch_info.cdp_endpoint,
            "ws_endpoint": launch_info.ws_endpoint,
            "pid": launch_info.pid,
            "launched_at": timezone.now().isoformat(),
        }
        account.metadata = meta
        account.save(update_fields=["metadata"])

        return Response(
            {
                "success": True,
                "created_profile": created_profile,
                "browser_type": BrowserType.GEEKEZ.value,
                "profile_id": launch_info.profile_id,
                "debug_port": launch_info.debug_port,
                "cdp_endpoint": launch_info.cdp_endpoint,
                "ws_endpoint": launch_info.ws_endpoint,
                "pid": launch_info.pid,
                "saved": True,
            }
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
            "overwrite_existing": false,
            "group_name": "售后",  // 可选，分组名称前缀
            "group_id": 1  // 可选，已存在的分组ID
        }
        """
        from apps.integrations.google_accounts.models import AccountGroup

        serializer = GoogleAccountImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        accounts_data = serializer.validated_data["accounts"]
        match_browser = serializer.validated_data["match_browser"]
        overwrite_existing = serializer.validated_data["overwrite_existing"]
        group_name_prefix = serializer.validated_data.get("group_name", "")
        group_id = serializer.validated_data.get("group_id")

        imported_count = 0
        skipped_count = 0
        errors = []
        accounts_list = []

        # 处理分组
        account_group = None
        if group_id:
            # 使用已存在的分组
            try:
                account_group = AccountGroup.objects.get(
                    id=group_id, owner_user=request.user
                )
            except AccountGroup.DoesNotExist:
                return Response(
                    {"error": f"分组ID {group_id} 不存在"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # 检查 group 字段是否存在（兼容迁移前）
            group_field_exists = False
            try:
                GoogleAccount._meta.get_field("group")
                group_field_exists = True
            except Exception:
                pass

            if group_field_exists:
                # 创建新分组，先预计算账号数量
                valid_account_count = 0
                for line in accounts_data:
                    parts = None
                    for separator in ["----", "---", "--", "|", "\t"]:
                        if separator in line:
                            parts = line.split(separator)
                            break
                    if parts and len(parts) >= 2 and "@" in parts[0]:
                        valid_account_count += 1

                if valid_account_count > 0:
                    # 生成分组名称
                    group_full_name = AccountGroup.generate_default_name(
                        prefix=group_name_prefix if group_name_prefix else None,
                        count=valid_account_count,
                    )
                    account_group = AccountGroup.objects.create(
                        name=group_full_name,
                        description=f"批量导入 {valid_account_count} 个账号",
                        owner_user=request.user,
                        account_count=0,  # 稍后更新
                    )

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
                # 智能检测分隔符：支持 ---- (4个), --- (3个), --, |, \t
                parts = None
                for separator in ["----", "---", "--", "|", "\t"]:
                    if separator in line:
                        parts = line.split(separator)
                        break

                if parts is None or len(parts) < 2:
                    errors.append(
                        f"Invalid format (no valid separator found): {line[:50]}..."
                    )
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
                        if secret:
                            existing.two_fa_secret = EncryptionUtil.encrypt(secret)
                            existing.two_fa_enabled = True
                        # 兼容迁移前后：只有 group 字段存在时才设置
                        if account_group and hasattr(existing, "group"):
                            existing.group = account_group
                        existing.save()
                        accounts_list.append(existing)
                        imported_count += 1
                    else:
                        skipped_count += 1
                        continue
                else:
                    # 创建新账号
                    create_kwargs = {
                        "owner_user": request.user,
                        "email": email,
                        "password": EncryptionUtil.encrypt(password),
                        "recovery_email": recovery,
                        "two_fa_secret": EncryptionUtil.encrypt(secret)
                        if secret
                        else "",
                        "two_fa_enabled": bool(secret),
                    }
                    # 兼容迁移前后：只有 group 字段存在时才添加
                    if account_group:
                        try:
                            # 检查模型是否有 group 字段
                            GoogleAccount._meta.get_field("group")
                            create_kwargs["group"] = account_group
                        except Exception:
                            pass

                    account = GoogleAccount.objects.create(**create_kwargs)
                    accounts_list.append(account)
                    imported_count += 1

            except Exception as e:
                errors.append(f"Error processing {line}: {str(e)}")
                logger.error(f"Import account error: {e}", exc_info=True)

        # 更新分组的账号数量
        if account_group:
            account_group.update_account_count()

        return Response(
            {
                "success": True,
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "errors": errors,
                "accounts": GoogleAccountSerializer(accounts_list, many=True).data,
                "group": {
                    "id": account_group.id,
                    "name": account_group.name,
                    "account_count": account_group.account_count,
                }
                if account_group
                else None,
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

        # 记录到账号 metadata（用于账号管理页展示最近操作历史）
        now_iso = timezone.now().isoformat()
        for acc in GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        ):
            meta = acc.metadata or {}
            actions = meta.get("google_zone_actions") or []
            actions.append(
                {
                    "kind": "security_change_2fa",
                    "celery_task_id": task.id,
                    "created_at": now_iso,
                    "browser_type": browser_type,
                }
            )
            meta["google_zone_actions"] = actions[-50:]
            acc.metadata = meta
            acc.save(update_fields=["metadata"])

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

        now_iso = timezone.now().isoformat()
        for acc in GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        ):
            meta = acc.metadata or {}
            actions = meta.get("google_zone_actions") or []
            actions.append(
                {
                    "kind": "security_change_recovery_email",
                    "celery_task_id": task.id,
                    "created_at": now_iso,
                    "browser_type": browser_type,
                    "new_email": new_email,
                }
            )
            meta["google_zone_actions"] = actions[-50:]
            acc.metadata = meta
            acc.save(update_fields=["metadata"])

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

        now_iso = timezone.now().isoformat()
        for acc in GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        ):
            meta = acc.metadata or {}
            actions = meta.get("google_zone_actions") or []
            actions.append(
                {
                    "kind": "security_get_backup_codes",
                    "celery_task_id": task.id,
                    "created_at": now_iso,
                    "browser_type": browser_type,
                }
            )
            meta["google_zone_actions"] = actions[-50:]
            acc.metadata = meta
            acc.save(update_fields=["metadata"])

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
        # 兼容前端历史字段名：new_email
        new_recovery_email = request.data.get("new_recovery_email") or request.data.get(
            "new_email"
        )
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

        now_iso = timezone.now().isoformat()
        for acc in GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        ):
            meta = acc.metadata or {}
            actions = meta.get("google_zone_actions") or []
            actions.append(
                {
                    "kind": "security_one_click",
                    "celery_task_id": task.id,
                    "created_at": now_iso,
                    "browser_type": browser_type,
                    "new_recovery_email": new_recovery_email,
                }
            )
            meta["google_zone_actions"] = actions[-50:]
            acc.metadata = meta
            acc.save(update_fields=["metadata"])

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

        now_iso = timezone.now().isoformat()
        for acc in GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        ):
            meta = acc.metadata or {}
            actions = meta.get("google_zone_actions") or []
            actions.append(
                {
                    "kind": "subscription_verify_status",
                    "celery_task_id": task.id,
                    "created_at": now_iso,
                    "browser_type": browser_type,
                    "take_screenshot": bool(take_screenshot),
                }
            )
            meta["google_zone_actions"] = actions[-50:]
            acc.metadata = meta
            acc.save(update_fields=["metadata"])

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

        now_iso = timezone.now().isoformat()
        for acc in GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        ):
            meta = acc.metadata or {}
            actions = meta.get("google_zone_actions") or []
            actions.append(
                {
                    "kind": "subscription_click_subscribe",
                    "celery_task_id": task.id,
                    "created_at": now_iso,
                    "browser_type": browser_type,
                }
            )
            meta["google_zone_actions"] = actions[-50:]
            acc.metadata = meta
            acc.save(update_fields=["metadata"])

        return Response(
            {
                "success": True,
                "task_id": task.id,
                "message": "点击订阅任务已提交",
            }
        )

    @action(detail=False, methods=["get"])
    def screenshot(self, request):
        """读取订阅验证生成的截图文件。

        订阅验证任务会把截图写入 backend 工作目录下的 `screenshots/`。
        前端通过文件名进行访问，避免路径穿越。

        GET /api/v1/plugins/google-business/subscription/screenshot/?file=xxx.png
        """

        import os
        from pathlib import Path
        from django.conf import settings

        filename = request.query_params.get("file")
        if not filename:
            return Response(
                {"error": "file required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 基本的路径穿越防护：只允许文件名
        filename = os.path.basename(filename)
        if not filename.lower().endswith(".png"):
            return Response(
                {"error": "invalid file"}, status=status.HTTP_400_BAD_REQUEST
            )

        screenshots_dir = (
            Path(getattr(settings, "BASE_DIR", Path.cwd())) / "screenshots"
        )
        file_path = (screenshots_dir / filename).resolve()

        try:
            if not file_path.is_file():
                return Response(
                    {"error": "file not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        except Exception:
            return Response(
                {"error": "file not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 额外校验：必须在 screenshots_dir 下
        try:
            if str(file_path).find(str(screenshots_dir.resolve())) != 0:
                return Response(
                    {"error": "invalid file"}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            pass

        return FileResponse(open(file_path, "rb"), content_type="image/png")


# ==================== 账号分组管理 ====================


class AccountGroupViewSet(viewsets.ModelViewSet):
    """
    账号分组管理

    提供分组的增删改查功能
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AccountGroupSerializer

    def get_queryset(self):
        return AccountGroup.objects.filter(owner_user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner_user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return AccountGroupCreateSerializer
        return AccountGroupSerializer

    @action(detail=True, methods=["get"])
    def accounts(self, request, pk=None):
        """
        获取分组下的所有账号

        GET /api/v1/plugins/google-business/groups/{id}/accounts/
        """
        group = self.get_object()
        accounts = GoogleAccount.objects.filter(group=group)

        # 支持分页
        page = self.paginate_queryset(accounts)
        if page is not None:
            serializer = GoogleAccountSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = GoogleAccountSerializer(accounts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_accounts(self, request, pk=None):
        """
        将账号添加到分组

        POST /api/v1/plugins/google-business/groups/{id}/add_accounts/
        {
            "account_ids": [1, 2, 3]
        }
        """
        group = self.get_object()
        account_ids = request.data.get("account_ids", [])

        if not account_ids:
            return Response(
                {"error": "请提供账号ID列表"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 更新账号的分组
        updated = GoogleAccount.objects.filter(
            id__in=account_ids, owner_user=request.user
        ).update(group=group)

        # 更新分组的账号数量
        group.update_account_count()

        return Response(
            {
                "success": True,
                "updated_count": updated,
                "group": AccountGroupSerializer(group).data,
            }
        )

    @action(detail=True, methods=["post"])
    def remove_accounts(self, request, pk=None):
        """
        将账号从分组中移除

        POST /api/v1/plugins/google-business/groups/{id}/remove_accounts/
        {
            "account_ids": [1, 2, 3]
        }
        """
        group = self.get_object()
        account_ids = request.data.get("account_ids", [])

        if not account_ids:
            return Response(
                {"error": "请提供账号ID列表"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 移除账号的分组（设为 null）
        updated = GoogleAccount.objects.filter(
            id__in=account_ids, group=group, owner_user=request.user
        ).update(group=None)

        # 更新分组的账号数量
        group.update_account_count()

        return Response(
            {
                "success": True,
                "removed_count": updated,
                "group": AccountGroupSerializer(group).data,
            }
        )

    @action(detail=False, methods=["get"])
    def list_with_counts(self, request):
        """
        获取所有分组及其账号数量

        GET /api/v1/plugins/google-business/groups/list_with_counts/
        """
        groups = self.get_queryset().annotate(actual_count=Count("accounts"))

        result = []
        for group in groups:
            data = AccountGroupSerializer(group).data
            data["actual_count"] = group.actual_count
            result.append(data)

        # 添加"未分组"的统计
        ungrouped_count = GoogleAccount.objects.filter(
            owner_user=request.user, group__isnull=True
        ).count()

        result.append(
            {
                "id": None,
                "name": "未分组",
                "description": "未分配到任何分组的账号",
                "account_count": ungrouped_count,
                "actual_count": ungrouped_count,
                "created_at": None,
                "updated_at": None,
            }
        )

        return Response(result)
