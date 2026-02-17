# ==================== 注册后引导页流程处理 ====================
# 从 oai-team-auto-provisioner/tools/onboarding_flow.py 移植
# 功能：处理 OpenAI 注册成功后的引导页流程（支持中英文双语）

import time
import random
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class Log:
    """简单的日志封装，兼容原代码"""
    def __init__(self, callback: Callable[[str], None] = None):
        self.callback = callback
    
    def _log(self, msg: str):
        logger.info(msg)
        if self.callback:
            self.callback(msg)
    
    def info(self, msg): self._log(msg)
    def success(self, msg): self._log(f"✓ {msg}")
    def warning(self, msg): self._log(f"⚠ {msg}")
    def error(self, msg): self._log(f"✗ {msg}")
    def step(self, msg): self._log(f"→ {msg}")
    def header(self, msg): self._log(f"=== {msg} ===")
    def separator(self): self._log("-" * 40)


log = Log()


def set_log_callback(callback: Callable[[str], None]):
    """设置日志回调"""
    global log
    log = Log(callback)


# ==================== 配置常量 ====================
STEP_TIMEOUT = 10
PAGE_WAIT = 5
HUMAN_DELAY = (0.5, 1.5)
STEP_DELAY = (2, 3)

# ==================== 测试数据 ====================
TEST_CHECKOUT_DATA = {
    "email": "test@example.com",
    "card_number": "4242424242424242",
    "card_expiry": "12/28",
    "card_cvc": "123",
    "cardholder_name": "",
    # 账单地址 (美国)
    "country": "US",
    "address_line1": "123 Test Street",
    "city": "New York",
    "postal_code": "10001",
    "state": "NY",
}


def _human_delay():
    """模拟人类操作间隔"""
    import random

    time.sleep(random.uniform(*HUMAN_DELAY))


def _step_delay():
    """步骤之间的随机延迟 (2-3秒)"""
    import random

    delay = random.uniform(*STEP_DELAY)
    log.info(f"等待 {delay:.1f}s...")
    time.sleep(delay)


def _wait_and_click(
    page, selector: str, timeout: int = STEP_TIMEOUT, required: bool = True
) -> bool:
    """等待元素出现并点击

    Args:
        page: 浏览器页面实例
        selector: 元素选择器 (支持 DrissionPage 语法)
        timeout: 超时时间
        required: 是否必须找到元素

    Returns:
        bool: 是否成功点击
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            element = page.ele(selector, timeout=1)
            if element and element.states.is_displayed:
                _human_delay()
                element.click()
                return True
        except Exception:
            pass
        time.sleep(0.3)

    if required:
        log.warning(f"未找到元素: {selector}")
    return False


def _find_element(page, selector: str, timeout: int = STEP_TIMEOUT):
    """查找元素

    Args:
        page: 浏览器页面实例
        selector: 元素选择器
        timeout: 超时时间

    Returns:
        元素对象或 None
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            element = page.ele(selector, timeout=1)
            if element and element.states.is_displayed:
                return element
        except Exception:
            pass
        time.sleep(0.3)

    return None


def _wait_for_url(page, url_contains: str, timeout: int = 30) -> bool:
    """等待 URL 包含指定字符串

    Args:
        page: 浏览器页面实例
        url_contains: URL 需要包含的字符串
        timeout: 超时时间

    Returns:
        bool: 是否成功
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            current_url = page.url
            if url_contains in current_url:
                return True
        except Exception:
            pass
        time.sleep(0.5)

    return False


def _is_checkout_url(current_url: str) -> bool:
    url = current_url or ""
    return (
        "chatgpt.com/checkout/openai_llc/" in url
        or "pay.openai.com" in url
    )


def _wait_for_checkout_url(page, timeout: int = 30) -> bool:
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            if _is_checkout_url(page.url):
                return True
        except Exception:
            pass
        time.sleep(0.5)

    return False


def _derive_cardholder_from_email(email: str) -> str:
    local = (email or "").split("@", 1)[0].strip()
    if not local:
        return ""

    normalized = local.replace(".", " ").replace("_", " ").replace("-", " ")
    parts = [part for part in normalized.split() if part]
    if not parts:
        return ""

    return " ".join(part.capitalize() for part in parts)


def _find_visible_input(context, selectors: list[str], timeout: int = 3):
    start_time = time.time()
    while time.time() - start_time < timeout:
        for selector in selectors:
            try:
                element = context.ele(selector, timeout=1)
                if element and element.states.is_displayed:
                    return element
            except Exception:
                pass
        time.sleep(0.2)
    return None


def _locate_stripe_frame(page, frame_type: str = "payment", timeout: int = 12):
    """使用 DrissionPage get_frame() 获取 Stripe iframe 上下文。

    Args:
        page: 浏览器页面实例
        frame_type: "payment" 或 "address"
        timeout: 超时时间

    Returns:
        ChromiumFrame 对象或 None
    """
    if frame_type == "payment":
        # 优先匹配 elements-inner-payment iframe
        frame_matchers = [
            '@src*=elements-inner-payment',
            '@title=Secure payment input frame',
            '@name*=privateStripeFrame',
        ]
    else:
        # address iframe
        frame_matchers = [
            '@src*=elements-inner-address',
            '@title=Secure address input frame',
        ]

    start_time = time.time()
    while time.time() - start_time < timeout:
        for matcher in frame_matchers:
            try:
                frame = page.get_frame(matcher)
                if frame:
                    return frame
            except Exception:
                pass
        time.sleep(0.5)

    # 兜底：按索引遍历所有 iframe
    try:
        frames = page.get_frames()
        for f in (frames or []):
            try:
                src = f.url or ""
                if frame_type == "payment" and "elements-inner-payment" in src:
                    return f
                if frame_type == "address" and "elements-inner-address" in src:
                    return f
            except Exception:
                pass
    except Exception:
        pass

    return None


def _fill_card_fields_in_iframe(page, data: dict) -> bool:
    frame_page = _locate_stripe_frame(page, frame_type="payment", timeout=10)
    if not frame_page:
        return False

    log.info("  检测到 Stripe payment iframe，进入 iframe 填写卡信息...")

    card_input = _find_visible_input(
        frame_page,
        [
            'css:input[name="cardnumber"]',
            'css:input[name="number"]',
            'css:input[autocomplete="cc-number"]',
            'input[name="cardnumber"]',
            'input[autocomplete="cc-number"]',
        ],
        timeout=4,
    )
    if card_input:
        _type_slowly(card_input, data["card_number"])
        log.success("  iframe 卡号已填写")
    else:
        log.warning("  iframe 未找到卡号输入框")

    _human_delay()

    expiry_input = _find_visible_input(
        frame_page,
        [
            'css:input[name="exp-date"]',
            'css:input[name="expiry"]',
            'css:input[autocomplete="cc-exp"]',
            'input[name="exp-date"]',
            'input[autocomplete="cc-exp"]',
        ],
        timeout=4,
    )
    if expiry_input:
        _type_slowly(expiry_input, data["card_expiry"])
        log.success("  iframe 有效期已填写")
    else:
        log.warning("  iframe 未找到有效期输入框")

    _human_delay()

    cvc_input = _find_visible_input(
        frame_page,
        [
            'css:input[name="cvc"]',
            'css:input[name="securityCode"]',
            'css:input[autocomplete="cc-csc"]',
            'input[name="cvc"]',
            'input[autocomplete="cc-csc"]',
        ],
        timeout=4,
    )
    if cvc_input:
        _type_slowly(cvc_input, data["card_cvc"])
        log.success("  iframe CVC 已填写")
    else:
        log.warning("  iframe 未找到 CVC 输入框")

    return bool(card_input and expiry_input and cvc_input)


def _fill_address_fields(page, data: dict) -> bool:
    """填写 Stripe address iframe 内的地址字段。

    新版 Stripe checkout 将持卡人姓名、地址、城市、邮编、州等放在
    独立的 address iframe (elements-inner-address) 中。
    如果无法进入 address iframe，则回退到主页面查找。
    """
    addr_frame = _locate_stripe_frame(page, frame_type="address", timeout=8)
    ctx = addr_frame if addr_frame else page
    ctx_label = "address iframe" if addr_frame else "主页面"
    if addr_frame:
        log.info(f"  检测到 Stripe address iframe，进入填写地址信息...")
    else:
        log.info(f"  未找到 address iframe，在主页面查找地址字段...")

    # 持卡人姓名
    log.info("  填写持卡人姓名...")
    name_input = _find_visible_input(
        ctx,
        [
            'css:input[name="name"]',
            'css:input[autocomplete="name"]',
            'css:input[name="billingName"]',
            'css:#billingName',
        ],
        timeout=5,
    )
    if name_input:
        _type_slowly(name_input, data.get("cardholder_name", ""))
        log.success(f"  持卡人姓名已填写 ({ctx_label})")
    else:
        log.warning(f"  未找到持卡人姓名输入框 ({ctx_label})")

    _human_delay()

    def _js_select_option(select_el, value: str, ctx_ref) -> bool:
        """用 JS 方式选择 <select> 的 option，兼容 Stripe iframe。"""
        try:
            # 方法 1: DrissionPage 原生 select
            select_el.select(value)
            return True
        except Exception:
            pass
        try:
            # 方法 2: JS 设置 value 并触发 change 事件
            js = """
            (function(sel, val) {
                for (var i = 0; i < sel.options.length; i++) {
                    if (sel.options[i].value === val || sel.options[i].text === val) {
                        sel.selectedIndex = i;
                        sel.value = sel.options[i].value;
                        sel.dispatchEvent(new Event('change', {bubbles: true}));
                        sel.dispatchEvent(new Event('input', {bubbles: true}));
                        return 'ok';
                    }
                }
                return 'not_found';
            })(arguments[0], arguments[1]);
            """.strip()
            result = ctx_ref.run_js(js, select_el, value, timeout=3) if hasattr(ctx_ref, 'run_js') else None
            if result == 'ok':
                return True
        except Exception:
            pass
        try:
            # 方法 3: 直接用 run_js_loaded 操作 select 元素
            select_el.run_js(f"""
                this.value = '{value}';
                this.dispatchEvent(new Event('change', {{bubbles: true}}));
                this.dispatchEvent(new Event('input', {{bubbles: true}}));
            """)
            return True
        except Exception:
            pass
        return False

    # 国家选择 — 默认 US，尝试选择
    log.info("  选择国家...")
    country_select = _find_visible_input(
        ctx,
        [
            'css:select[name="countryCode"]',
            'css:select[autocomplete="country"]',
            'css:select[name="country"]',
            'css:#billingCountry',
        ],
        timeout=3,
    )
    if country_select:
        country_val = data.get("country", "US")
        if _js_select_option(country_select, country_val, ctx):
            log.success(f"  国家已选择 ({ctx_label})")
            time.sleep(0.5)
        else:
            log.warning(f"  选择国家失败 ({ctx_label})")
    else:
        log.info(f"  跳过国家选择(使用默认值)")

    _human_delay()

    # 地址
    log.info("  填写地址...")
    addr_input = _find_visible_input(
        ctx,
        [
            'css:input[name="addressLine1"]',
            'css:input[autocomplete="address-line1"]',
            'css:input[name="line1"]',
            'css:#billingAddressLine1',
        ],
        timeout=5,
    )
    if addr_input:
        _type_slowly(addr_input, data.get("address_line1", ""))
        log.success(f"  地址已填写 ({ctx_label})")
        # 等待地址自动补全消失
        time.sleep(1)
    else:
        log.warning(f"  未找到地址输入框 ({ctx_label})")

    _human_delay()

    # 城市
    log.info("  填写城市...")
    city_input = _find_visible_input(
        ctx,
        [
            'css:input[name="locality"]',
            'css:input[autocomplete="address-level2"]',
            'css:input[name="city"]',
            'css:#billingLocality',
        ],
        timeout=5,
    )
    if city_input:
        _type_slowly(city_input, data.get("city", ""))
        log.success(f"  城市已填写 ({ctx_label})")

    _human_delay()

    # 州
    log.info("  选择州...")
    state_select = _find_visible_input(
        ctx,
        [
            'css:select[name="administrativeArea"]',
            'css:select[autocomplete="address-level1"]',
            'css:select[name="state"]',
            'css:#billingAdministrativeArea',
        ],
        timeout=5,
    )
    if state_select:
        state_val = data.get("state", "NY")
        if _js_select_option(state_select, state_val, ctx):
            log.success(f"  州已选择 ({ctx_label})")
        else:
            log.warning(f"  选择州失败 ({ctx_label})")

    _human_delay()

    # 邮编
    log.info("  填写邮编...")
    postal_input = _find_visible_input(
        ctx,
        [
            'css:input[name="postalCode"]',
            'css:input[autocomplete="postal-code"]',
            'css:input[name="zip"]',
            'css:#billingPostalCode',
        ],
        timeout=5,
    )
    if postal_input:
        _type_slowly(postal_input, data.get("postal_code", ""))
        log.success(f"  邮编已填写 ({ctx_label})")

    _human_delay()
    return True


def _type_slowly(element, text: str, base_delay: float = 0.08):
    """缓慢输入文本 (模拟真人)

    Args:
        element: 输入框元素
        text: 要输入的文本
        base_delay: 基础延迟
    """
    import random

    if not text:
        return

    # 先确保清空已有内容
    try:
        element.clear()
        time.sleep(0.15)
    except Exception:
        pass

    # 短文本直接输入
    if len(text) <= 8:
        element.input(text, clear=True)
        return

    # 长文本逐字输入
    element.input(text[0], clear=True)
    time.sleep(random.uniform(0.1, 0.2))

    for char in text[1:]:
        element.input(char, clear=False)
        actual_delay = base_delay * random.uniform(0.5, 1.2)
        if char in " @._-":
            actual_delay *= 1.3
        time.sleep(actual_delay)


# ==================== 配置加载 ====================
def load_checkout_config(checkout_data: dict = None):
    """加载结算配置
    
    Args:
        checkout_data: 外部传入的结算数据，如果提供则直接使用
    """
    default_data = TEST_CHECKOUT_DATA.copy()
    
    if checkout_data:
        for key in default_data:
            if key in checkout_data:
                default_data[key] = checkout_data[key]
        return default_data
    
    return default_data

# ==================== 引导页流程步骤 ====================


def _log_current_url(page, context: str = ""):
    """记录当前页面 URL"""
    try:
        url = page.url
        if context:
            log.info(f"[URL] {context} | {url}")
        else:
            log.info(f"[URL] {url}")
    except Exception:
        pass


def step_start_business_trial(page) -> bool:
    """步骤: 点击 '开始 Business 试用'
    
    新版流程的第一步
    """
    log.step("查找 '开始 Business 试用' 按钮...")
    _log_current_url(page, "初始页面")
    
    if _wait_and_click(page, "text:开始 Business 试用", timeout=5, required=False):
        log.success("已点击 '开始 Business 试用'")
        return True
        
    if _wait_and_click(page, "text:Start Business trial", timeout=3, required=False):
        log.success("已点击 'Start Business trial'")
        return True
        
    log.info("未找到试用按钮，继续下一步...")
    return False


def step_lets_go_popup(page) -> bool:
    """步骤: 点击 '开始吧' / 'Let's go' 弹窗"""
    log.step("检查 '开始吧' 弹窗...")
    time.sleep(1)
    
    if _wait_and_click(page, "text:开始吧", timeout=3, required=False):
        log.success("已点击 '开始吧'")
        return True
        
    if _wait_and_click(page, "text:Let's go", timeout=2, required=False):
        log.success("已点击 'Let's go'")
        return True
        
    if _wait_and_click(page, "text:Get started", timeout=2, required=False):
        log.success("已点击 'Get started'")
        return True

    return False


def step_dismiss_popups(page, max_attempts: int = 3) -> bool:
    """步骤 1-2: 处理初始弹窗 (跳过)

    元素: <div class="flex items-center justify-center">跳过</div>
    """
    log.step("步骤 1: 检查初始弹窗...")
    _log_current_url(page, "弹窗检测")
    handled = False

    for i in range(max_attempts):
        # 文本匹配 "跳过"
        if _wait_and_click(page, "text:跳过", timeout=3, required=False):
            log.success(f"  已点击跳过按钮 ({i + 1})")
            handled = True
            time.sleep(1)
            continue

        # 英文 Skip
        if _wait_and_click(page, "text:Skip", timeout=2, required=False):
            log.success(f"  已点击 Skip 按钮 ({i + 1})")
            handled = True
            time.sleep(1)
            continue

        break

    if not handled:
        log.info("  未检测到弹窗，继续...")

    return handled


def step_skip_tour(page) -> bool:
    """步骤 3: 跳过导览"""
    log.step("步骤 2: 查找跳过导览按钮...")
    _log_current_url(page, "导览页面")
    time.sleep(2)

    if _wait_and_click(page, "text:跳过导览", timeout=5, required=False):
        log.success("  已跳过导览")
        return True

    if _wait_and_click(page, "text:Skip tour", timeout=3, required=False):
        log.success("  已跳过导览")
        return True

    log.info("  未找到跳过导览按钮，继续...")
    return False


def step_click_continue(page) -> bool:
    """步骤 4: 点击继续"""
    log.step("步骤 3: 点击继续...")
    _log_current_url(page, "继续按钮页面")

    last_url = None
    for attempt in range(12):
        try:
            current_url = page.url
            if last_url != current_url:
                last_url = current_url
        except Exception:
            current_url = ""

        btn = None
        try:
            btn = page.ele("css:button.btn.btn-primary.btn-large.w-full", timeout=1)
        except Exception:
            btn = None

        if not btn:
            try:
                btn = page.ele("css:button.btn-primary.btn-large.w-full", timeout=1)
            except Exception:
                btn = None

        if not btn:
            try:
                btn = page.ele("css:button.btn-primary.btn-large", timeout=1)
            except Exception:
                btn = None

        if btn and btn.states.is_displayed and btn.states.is_enabled:
            try:
                btn_text = (btn.text or "").strip().lower()
                if ("继续" in btn_text) or ("continue" in btn_text):
                    _human_delay()
                    btn.click()
                    log.success("  已点击继续")
                    time.sleep(1)
                    return True
            except Exception:
                pass

        try:
            buttons = page.eles("css:button.btn-primary")
            for b in buttons:
                if b.states.is_displayed and b.states.is_enabled:
                    t = (b.text or "").strip().lower()
                    if ("继续" in t) or ("continue" in t):
                        _human_delay()
                        b.click()
                        log.success("  已点击继续")
                        time.sleep(1)
                        return True
        except Exception:
            pass

        if attempt < 11:
            log.info(f"  重试 ({attempt + 1}/12)...")
            time.sleep(1)

    log.warning("  未找到继续按钮")
    return False


def step_select_free_gift(page) -> bool:
    """步骤 5: 选择免费赠品"""
    log.step("步骤 4: 选择免费赠品...")
    _log_current_url(page, "免费赠品页面")

    for attempt in range(5):
        if _wait_and_click(page, "text:免费赠品", timeout=3, required=False):
            log.success("  已选择免费赠品 (text)")
            return True

        if _wait_and_click(page, "text:Free gift", timeout=2, required=False):
            log.success("  已选择免费赠品 (Free gift)")
            return True

        try:
            buttons = page.eles("css:button")
            for btn in buttons:
                if btn.states.is_displayed and btn.states.is_enabled:
                    btn_text = btn.text.strip().lower()
                    if "免费" in btn_text or "free" in btn_text or "赠品" in btn_text or "gift" in btn_text:
                        _human_delay()
                        btn.click()
                        log.success(f"  已选择免费赠品 (按钮遍历: {btn_text[:20]})")
                        return True
        except Exception:
            pass

        if _wait_and_click(page, "css:button.bg-transparent", timeout=2, required=False):
            log.success("  已选择免费赠品 (bg-transparent)")
            return True

        if attempt < 4:
            log.info(f"  重试 ({attempt + 1}/5)...")
            time.sleep(1.5)

    log.warning("  未找到免费赠品选项")
    return False


def step_select_business(page) -> bool:
    """步骤 6: 选择 Business 套餐

    元素: <button class="btn relative btn-purple btn-large w-full"
                 data-testid="select-plan-button-teams-create">
            <div class="flex items-center justify-center">获取 Business</div>
          </button>

    Args:
        page: 浏览器页面实例

    Returns:
        bool: 是否成功
    """
    log.step("选择 Business 套餐...")

    # 方法1: 通过 data-testid 定位 (最精确)
    if _wait_and_click(
        page,
        'css:button[data-testid="select-plan-button-teams-create"]',
        timeout=STEP_TIMEOUT,
        required=False,
    ):
        log.success("已选择 Business 套餐")
        return True

    # 方法2: 通过 btn-purple 类定位
    if _wait_and_click(page, "css:button.btn-purple", timeout=5, required=False):
        log.success("已选择 Business 套餐")
        return True

    # 方法3: 文本匹配
    if _wait_and_click(page, "text:获取 Business", timeout=5, required=False):
        log.success("已选择 Business 套餐")
        return True

    # 方法4: 英文
    if _wait_and_click(page, "text:Get Business", timeout=3, required=False):
        log.success("已选择 Business 套餐")
        return True

    log.warning("未找到 Business 套餐选项")
    return False


def step_continue_checkout(page) -> bool:
    """步骤 7: 继续结算

    元素: <button class="btn relative btn-green mt-8 w-full rounded-xl">
            <div class="flex items-center justify-center">继续结算</div>
          </button>

    Args:
        page: 浏览器页面实例

    Returns:
        bool: 是否成功
    """
    log.step("点击继续结算...")

    # 方法1: 通过 btn-green 类定位
    if _wait_and_click(
        page, "css:button.btn-green", timeout=STEP_TIMEOUT, required=False
    ):
        log.success("已点击继续结算")
        return True

    # 方法2: 文本匹配
    if _wait_and_click(page, "text:继续结算", timeout=5, required=False):
        log.success("已点击继续结算")
        return True

    # 方法3: 英文
    if _wait_and_click(page, "text:Continue to checkout", timeout=3, required=False):
        log.success("已点击继续结算")
        return True

    log.warning("未找到继续结算按钮")
    return False


def step_fill_checkout_form(
    page,
    email_override: str = "",
    card_number_override: str = "",
    card_expiry_override: str = "",
    card_cvc_override: str = "",
    cardholder_override: str = "",
    address_override: str = "",
    city_override: str = "",
    postal_override: str = "",
    state_override: str = "",
) -> bool:
    log.step("等待支付页面加载...")

    # 等待跳转到新版 checkout 页面
    if not _wait_for_checkout_url(page, timeout=30):
        log.warning(f"未跳转到支付页面，当前URL: {page.url}")
        return False

    log.success(f"已进入支付页面: {page.url}")
    _step_delay()

    log.step("填写结算表单...")

    data = load_checkout_config()
    
    if email_override:
        data["email"] = email_override
    if card_number_override:
        data["card_number"] = card_number_override
    if card_expiry_override:
        data["card_expiry"] = card_expiry_override
    if card_cvc_override:
        data["card_cvc"] = card_cvc_override
    if cardholder_override:
        data["cardholder_name"] = cardholder_override
    if address_override:
        data["address_line1"] = address_override
    if city_override:
        data["city"] = city_override
    if postal_override:
        data["postal_code"] = postal_override
    if state_override:
        data["state"] = state_override

    holder_name = str(data.get("cardholder_name") or "").strip()
    if not holder_name or holder_name.lower() == "test user":
        fallback_holder = _derive_cardholder_from_email(email_override or data.get("email", ""))
        if fallback_holder:
            data["cardholder_name"] = fallback_holder

    log.info("  填写邮箱...")
    email_input = _find_element(page, "css:#email", timeout=5)
    if email_input:
        # 先清空再输入，防止追加导致重复
        try:
            email_input.clear()
            time.sleep(0.2)
        except Exception:
            pass
        _type_slowly(email_input, data["email"])
        log.success("  邮箱已填写")
    else:
        log.warning("  未找到邮箱输入框")

    _human_delay()

    # 2-4. 填写卡号/有效期/CVC（Stripe payment iframe）
    if not _fill_card_fields_in_iframe(page, data):
        log.info("  回退到 legacy 输入框模式填写卡信息...")

        log.info("  填写银行卡...")
        card_input = _find_element(page, "css:#cardNumber", timeout=5)
        if card_input:
            _type_slowly(card_input, data["card_number"])
            log.success("  银行卡已填写")
        else:
            log.warning("  未找到银行卡输入框")

        _human_delay()

        log.info("  填写有效期...")
        expiry_input = _find_element(page, "css:#cardExpiry", timeout=5)
        if expiry_input:
            _type_slowly(expiry_input, data["card_expiry"])
            log.success("  有效期已填写")
        else:
            log.warning("  未找到有效期输入框")

        _human_delay()

        log.info("  填写 CVC...")
        cvc_input = _find_element(page, "css:#cardCvc", timeout=5)
        if cvc_input:
            _type_slowly(cvc_input, data["card_cvc"])
            log.success("  CVC 已填写")
        else:
            log.warning("  未找到 CVC 输入框")

    _human_delay()

    # 5-10. 持卡人姓名/国家/地址/城市/邮编/州 — 在 Stripe address iframe 内
    _fill_address_fields(page, data)

    # 11. 勾选许可协议
    log.info("  勾选许可协议...")
    checkbox = _find_element(page, 'css:input[type="checkbox"]', timeout=3)
    if checkbox:
        try:
            if not checkbox.states.is_checked:
                checkbox.click()
                log.success("  已勾选许可协议")
            else:
                log.info("  许可协议已勾选")
        except Exception:
            pass

    _human_delay()

    # 12. 点击订阅/支付按钮
    log.step("点击订阅按钮...")
    # 查找订阅按钮 (通常包含 'Subscribe', 'Pay', '订阅' 等文字)
    subscribe_btn = None
    
    # 尝试多种选择器
    selectors = [
        'css:button[type="submit"]',
        'css:button.SubmitButton',
        'text:订阅',
        'text:Subscribe',
        'text:Pay',
        'text:Start plan',
    ]
    
    for sel in selectors:
        try:
            btn = page.ele(sel, timeout=1)
            if btn and btn.states.is_displayed and btn.states.is_enabled:
                subscribe_btn = btn
                break
        except Exception:
            pass
            
    if subscribe_btn:
        try:
            subscribe_btn.click()
            log.success("已点击订阅按钮")
        except Exception as e:
            log.warning(f"点击订阅按钮失败: {e}")
    else:
        log.warning("未找到订阅按钮，请手动点击")

    log.success("表单填写完成")
    return True


def step_payment_success_continue(page) -> bool:
    """步骤 9: 智能等待付款成功并点击继续
    
    实时监听 URL 变化，一旦检测到成功页面立即响应
    """
    # 最大等待时间 (5分钟)
    MAX_WAIT = 300
    CHECK_INTERVAL = 1  # 每秒检查一次
    
    log.step(f"等待付款成功页面 (最大超时: {MAX_WAIT}秒)...")
    log.info("请在此期间手动完成 3D 验证或人机验证...")
    _log_current_url(page, "等待付款前")

    start_time = time.time()
    success_detected = False
    
    while time.time() - start_time < MAX_WAIT:
        try:
            current_url = page.url
            # 检测成功 URL 特征
            if "chatgpt.com/payments/success" in current_url:
                log.success(f"检测到付款成功页面! ({int(time.time() - start_time)}s)")
                _log_current_url(page, "付款成功页")
                success_detected = True
                break
                
            # 可选: 检测是否还在支付流程中
            if (
                "chatgpt.com/checkout/openai_llc/" in current_url
                or "pay.openai.com" in current_url
                or "stripe.com" in current_url
            ):
                # 还在支付流程中，继续等待
                pass
            
            # 每 10 秒打印一次心跳，避免用户以为卡死
            elapsed = int(time.time() - start_time)
            if elapsed > 0 and elapsed % 10 == 0:
                # 只在控制台显示，不记录到 log 文件以免刷屏 (如果 logger 支持的话)
                pass 
                
        except Exception:
            pass
            
        time.sleep(CHECK_INTERVAL)

    if not success_detected:
        log.warning("等待超时，未检测到付款成功页面 (但这可能只是 URL 没变，尝试继续...)")
        _log_current_url(page, "超时后页面")

    _step_delay()

    # 点击继续
    log.step("尝试点击继续按钮...")
    if _wait_and_click(
        page, "css:button.btn-primary", timeout=STEP_TIMEOUT, required=False
    ):
        log.success("已点击继续")
        return True

    if _wait_and_click(page, "text:继续", timeout=5, required=False):
        log.success("已点击继续")
        return True

    log.warning("未找到继续按钮")
    return False


def step_skip_team_name(page) -> bool:
    """步骤 10: 跳过团队名称输入，直接点击继续

    元素: <button class="btn relative btn-primary btn-large w-full">
            <div class="flex items-center justify-center">继续</div>
          </button>

    Args:
        page: 浏览器页面实例

    Returns:
        bool: 是否成功
    """
    log.step("跳过团队名称，点击继续...")
    _step_delay()

    if _wait_and_click(
        page, "css:button.btn-primary", timeout=STEP_TIMEOUT, required=False
    ):
        log.success("已跳过团队名称")
        return True

    if _wait_and_click(page, "text:继续", timeout=5, required=False):
        log.success("已跳过团队名称")
        return True

    log.warning("未找到继续按钮")
    return False


def step_get_session_data(page) -> dict:
    """步骤 11: 获取 session 数据

    打开 https://chatgpt.com/api/auth/session 获取 JSON 数据

    Args:
        page: 浏览器页面实例

    Returns:
        dict: session 数据，失败返回空字典
    """
    import json

    log.step("获取 session 数据...")
    _step_delay()

    try:
        # 打开 session API
        page.get("https://chatgpt.com/api/auth/session")
        time.sleep(2)

        # 获取页面内容 (JSON)
        page_text = page.ele("css:pre").text if page.ele("css:pre") else page.html

        # 解析 JSON
        session_data = json.loads(page_text)
        log.success("已获取 session 数据")
        log.info(f"Session 数据: {json.dumps(session_data, indent=2, ensure_ascii=False)}")
        return session_data

    except Exception as e:
        log.error(f"获取 session 数据失败: {e}")
        return {}


def step_keep_browser_open(page):
    """步骤 9: 保持浏览器打开等待人工检查

    Args:
        page: 浏览器页面实例
    """
    log.header("引导流程完成，浏览器保持打开")
    log.info("请检查页面状态...")
    log.info("按 Ctrl+C 可关闭浏览器")

    try:
        current_url = page.url
        log.info(f"当前 URL: {current_url}")
    except Exception:
        pass

    log.separator()

    # 无限等待，直到用户中断
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.warning("用户中断，准备关闭...")


# ==================== 主流程函数 ====================


def step_inject_promo_checkout(page) -> bool:
    """步骤: 注入 JS 强制跳转到带优惠的结算页
    
    使用 team-1-month-free 优惠码直接调用 API
    """
    log.step("注入优惠码并跳转结算页...")

    workspace_name = f"pigll{random.randint(0, 99999):05d}"
    log.info(f"本次工作区名称: {workspace_name}")
    
    js_code = """
    (async function (){
        try {
            const t = await (await fetch("/api/auth/session")).json();
            if (!t.accessToken){
                return "NO_TOKEN";
            } 
            const p = {
                plan_name: "chatgptteamplan",
                team_plan_data: {
                    workspace_name: "__WORKSPACE_NAME__",
                    price_interval: "month",
                    seat_quantity: 5
                },
                promo_campaign: {
                    promo_campaign_id: "team-1-month-free",
                    is_coupon_from_query_param: true
                },
                checkout_ui_mode: "custom"
            };
            const r = await fetch("https://chatgpt.com/backend-api/payments/checkout", {
                method: "POST",
                headers: {
                    Authorization: "Bearer " + t.accessToken,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(p)
            });
            const d = await r.json();
            if (d.checkout_session_id) {
                window.location.href = "https://chatgpt.com/checkout/openai_llc/" + d.checkout_session_id;
                return "SUCCESS";
            } else {
                return "ERROR: " + (d.detail || JSON.stringify(d));
            }
        } catch (e) {
            return "EXCEPTION: " + e;
        }
    })();
    """

    js_code = js_code.replace("__WORKSPACE_NAME__", workspace_name)
    
    try:
        # 确保先加载主页以获取 context
        if "chatgpt.com" not in page.url:
            page.get("https://chatgpt.com")
            time.sleep(3)
            
        result = page.run_js(js_code)
        log.info(f"JS 执行结果: {result}")
        
        if result == "NO_TOKEN":
            log.warning("未检测到 accessToken，可能未登录")
            return False
            
        # 等待跳转
        if _wait_for_checkout_url(page, timeout=25):
            log.success(f"成功跳转到结算页: {page.url}")
            return True
            
        log.warning("未跳转到支付页面 (JS执行看似成功但URL未变)")
        return False
        
    except Exception as e:
        log.error(f"注入 JS 失败: {e}")
        return False


def run_onboarding_flow(
    page,
    email: str = "",
    card_number: str = "",
    cardholder_name: str = "",
    address: str = "",
    skip_checkout: bool = False,
    get_card_callback: Optional[Callable[[], Optional[dict]]] = None,
    card_wait_timeout: int = 300,
) -> tuple[bool, dict]:
    """执行完整的引导页流程 (JS 注入模式)

    Args:
        page: 浏览器页面实例 (已登录状态)
        email: 结算邮箱 (可选)
        card_number: 银行卡号 (可选)
        cardholder_name: 持卡人姓名 (可选)
        address: 地址 (可选)
        skip_checkout: 是否跳过结算表单填写
        get_card_callback: 获取可用卡的回调函数，返回卡信息字典或 None
        card_wait_timeout: 等待卡的超时时间（秒）

    Returns:
        tuple: (是否成功, session数据)
    """
    log.header("开始引导页流程 (JS 注入模式)")

    try:
        # 步骤 1: 处理初始弹窗 (如果有)
        _log_current_url(page, "开始前")
        step_dismiss_popups(page, max_attempts=1)

        # 步骤 2: 注入优惠码并跳转
        _log_current_url(page, "注入JS前")
        if not step_inject_promo_checkout(page):
            log.error("无法跳转到优惠结算页，流程终止")
            return False, {}

        # 步骤 3: 等待获取可用卡（如果需要填表单且有回调）
        card_info = None
        if not skip_checkout and get_card_callback:
            log.step(f"等待可用卡（最多 {card_wait_timeout} 秒）...")
            import time as time_module
            wait_start = time_module.time()
            
            while time_module.time() - wait_start < card_wait_timeout:
                try:
                    card_info = get_card_callback()
                except Exception as e:
                    log.warning(f"获取卡失败: {e}")
                    card_info = None
                
                if card_info:
                    log.success(f"获取到可用卡: ****{card_info.get('card_number', '')[-4:]}")
                    break
                
                elapsed = int(time_module.time() - wait_start)
                log.info(f"无可用卡，等待中... ({elapsed}s/{card_wait_timeout}s)")
                time_module.sleep(10)
            
            if not card_info:
                log.error(f"等待 {card_wait_timeout} 秒后仍无可用卡，流程终止")
                return False, {}

        # 步骤 4: 填写结算表单
        _log_current_url(page, "填写表单前")
        if not skip_checkout:
            # 如果有卡信息，使用卡信息覆盖
            if card_info:
                cardholder_value = card_info.get("cardholder_name", "") or cardholder_name
                step_fill_checkout_form(
                    page,
                    email_override=email,
                    card_number_override=card_info.get("card_number", ""),
                    card_expiry_override=card_info.get("card_expiry", ""),
                    card_cvc_override=card_info.get("card_cvc", ""),
                    cardholder_override=cardholder_value,
                    address_override=card_info.get("address_line1", ""),
                    city_override=card_info.get("city", ""),
                    postal_override=card_info.get("postal_code", ""),
                    state_override=card_info.get("state", ""),
                )
            else:
                step_fill_checkout_form(
                    page,
                    email_override=email,
                    cardholder_override=cardholder_name,
                )
        else:
            log.info("跳过结算表单填写")

        # 步骤 4: 付款成功后点击继续 (包含智能等待)
        step_payment_success_continue(page)

        # 步骤 5: 跳过团队名称
        _log_current_url(page, "跳过团队名前")
        step_skip_team_name(page)

        # 步骤 6: 获取 session 数据
        _log_current_url(page, "获取Session前")
        session_data = step_get_session_data(page)

        log.success("引导流程执行完成")
        return True, session_data

    except Exception as e:
        log.error(f"引导流程异常: {e}")
        return False, {}


def run_onboarding_and_wait(
    page,
    email: str = "",
    card_number: str = "",
    cardholder_name: str = "",
    address: str = "",
    skip_checkout: bool = False,
):
    """执行引导流程并保持浏览器打开

    Args:
        page: 浏览器页面实例
        email: 结算邮箱
        card_number: 银行卡号
        cardholder_name: 持卡人姓名
        address: 地址
        skip_checkout: 是否跳过结算表单
    """
    success, session_data = run_onboarding_flow(
        page,
        email=email,
        card_number=card_number,
        cardholder_name=cardholder_name,
        address=address,
        skip_checkout=skip_checkout,
    )

    # 保持浏览器打开
    step_keep_browser_open(page)

    return success, session_data
