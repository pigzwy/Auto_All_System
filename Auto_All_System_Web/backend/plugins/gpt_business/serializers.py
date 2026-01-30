from rest_framework import serializers


class GptMailSettingsSerializer(serializers.Serializer):
    api_base = serializers.URLField(required=True)
    api_key = serializers.CharField(required=True, trim_whitespace=True)
    prefix = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    domains = serializers.ListField(
        child=serializers.CharField(trim_whitespace=True),
        required=False,
        allow_empty=True,
    )


class TeamSettingsSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, trim_whitespace=True)
    # Team Owner 的 accessToken（可选；为空则走 DrissionPage 登录获取）
    auth_token = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    account_id = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    owner_email = serializers.EmailField(required=False, allow_blank=False)
    owner_password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    authorized = serializers.BooleanField(required=False)


class ProxySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["http", "https"], required=True)
    host = serializers.CharField(required=True, trim_whitespace=True)
    port = serializers.IntegerField(required=True, min_value=1, max_value=65535)
    username = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)


class CrsSettingsSerializer(serializers.Serializer):
    api_base = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    admin_token = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)


class CpaSettingsSerializer(serializers.Serializer):
    api_base = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    admin_password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    poll_interval = serializers.IntegerField(required=False, min_value=1, max_value=60)
    poll_max_retries = serializers.IntegerField(required=False, min_value=1, max_value=600)
    is_webui = serializers.BooleanField(required=False)


class S2aSettingsSerializer(serializers.Serializer):
    api_base = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    admin_key = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    admin_token = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    concurrency = serializers.IntegerField(required=False, min_value=1, max_value=50)
    priority = serializers.IntegerField(required=False, min_value=0, max_value=999)
    group_ids = serializers.ListField(child=serializers.IntegerField(), required=False, allow_empty=True)
    group_names = serializers.ListField(child=serializers.CharField(trim_whitespace=True), required=False, allow_empty=True)


class RequestSettingsSerializer(serializers.Serializer):
    timeout = serializers.IntegerField(required=False, min_value=1, max_value=120)
    user_agent = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)


class VerificationSettingsSerializer(serializers.Serializer):
    timeout = serializers.IntegerField(required=False, min_value=5, max_value=600)
    interval = serializers.IntegerField(required=False, min_value=1, max_value=60)
    max_retries = serializers.IntegerField(required=False, min_value=1, max_value=300)


class BrowserSettingsSerializer(serializers.Serializer):
    wait_timeout = serializers.IntegerField(required=False, min_value=5, max_value=600)
    short_wait = serializers.IntegerField(required=False, min_value=1, max_value=120)
    headless = serializers.BooleanField(required=False)


class CheckoutSettingsSerializer(serializers.Serializer):
    card_number = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    card_expiry = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    card_cvc = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    cardholder_name = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    address_line1 = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    city = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    postal_code = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    state = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    country = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)


class SettingsUpdateSerializer(serializers.Serializer):
    gptmail = GptMailSettingsSerializer(required=False)
    teams = serializers.ListField(child=TeamSettingsSerializer(), required=False, allow_empty=True)

    # legacy / full-run 配置（对应 oai-team-auto-provisioner 的 config.toml.example）
    legacy_repo_path = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    proxy_enabled = serializers.BooleanField(required=False)
    proxies = serializers.ListField(child=ProxySerializer(), required=False, allow_empty=True)
    auth_provider = serializers.ChoiceField(choices=["crs", "cpa", "s2a"], required=False)
    include_team_owners = serializers.BooleanField(required=False)
    crs = CrsSettingsSerializer(required=False)
    cpa = CpaSettingsSerializer(required=False)
    s2a = S2aSettingsSerializer(required=False)
    request = RequestSettingsSerializer(required=False)
    verification = VerificationSettingsSerializer(required=False)
    browser = BrowserSettingsSerializer(required=False)
    checkout = CheckoutSettingsSerializer(required=False)

    default_password = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    accounts_per_team = serializers.IntegerField(required=False, min_value=1, max_value=50)


class TaskCreateSerializer(serializers.Serializer):
    flow = serializers.ChoiceField(choices=["invite_only", "legacy_run"], required=False)
    team_name = serializers.CharField(required=True, trim_whitespace=True)
    count = serializers.IntegerField(required=False, min_value=1, max_value=50)
    password = serializers.CharField(required=False, trim_whitespace=False)
    legacy_args = serializers.ListField(child=serializers.CharField(trim_whitespace=True), required=False, allow_empty=True)


class AccountCreateMotherSerializer(serializers.Serializer):
    # 选中 /admin/email 的配置
    cloudmail_config_id = serializers.IntegerField(required=True, min_value=1)
    # 指定域名（可选）；不填则在该配置的 domains 中随机
    domain = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    # 生成数量
    count = serializers.IntegerField(required=False, min_value=1, max_value=200, default=1)
    # 母号座位数（默认 4；可后续更新）
    seat_total = serializers.IntegerField(required=False, min_value=0, max_value=500, default=4)
    note = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)


class AccountCreateChildSerializer(serializers.Serializer):
    parent_id = serializers.CharField(required=True, trim_whitespace=True)
    # 可选：不传则默认跟随母号的 cloudmail_config_id
    cloudmail_config_id = serializers.IntegerField(required=False, min_value=1)
    domain = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    count = serializers.IntegerField(required=False, min_value=1, max_value=500, default=1)
    note = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)


class AccountUpdateSerializer(serializers.Serializer):
    seat_total = serializers.IntegerField(required=False, min_value=0, max_value=500)
    note = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)


class AccountLaunchGeekezSerializer(serializers.Serializer):
    # 仅为扩展预留：未来可以让前端传 proxy 等信息
    pass
