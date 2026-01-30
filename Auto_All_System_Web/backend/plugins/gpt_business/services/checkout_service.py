"""
绑卡开通服务 - 自动完成 OpenAI Plus 订阅开通
"""
import logging
import time
from dataclasses import dataclass
from typing import Any

from .browser_service import BrowserService

logger = logging.getLogger(__name__)


@dataclass
class CardInfo:
    """信用卡信息"""
    card_number: str
    expiry: str
    cvv: str
    holder_name: str
    address_line1: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


@dataclass
class CheckoutResult:
    """开通结果"""
    success: bool
    error: str = ""


class CheckoutService:
    """绑卡开通服务"""

    UPGRADE_URL = "https://chatgpt.com/#pricing"
    PAY_URL_PREFIX = "https://pay.openai.com"

    def __init__(self, browser: BrowserService):
        self.browser = browser

    def checkout(self, email: str, card: CardInfo) -> CheckoutResult:
        """
        完成订阅开通
        
        流程:
        1. 点击升级按钮
        2. 选择订阅计划
        3. 填写信用卡信息
        4. 提交支付
        """
        try:
            logger.info(f"开始订阅开通: {email}")

            if not self._step_go_to_upgrade():
                return CheckoutResult(False, "进入升级页面失败")

            if not self._step_select_plan():
                return CheckoutResult(False, "选择订阅计划失败")

            if not self._step_fill_payment(email, card):
                return CheckoutResult(False, "填写支付信息失败")

            if not self._step_submit_payment():
                return CheckoutResult(False, "提交支付失败")

            if not self._wait_for_success():
                return CheckoutResult(False, "等待支付完成超时")

            logger.info(f"订阅开通成功: {email}")
            return CheckoutResult(True)

        except Exception as e:
            logger.exception(f"订阅开通异常: {email}")
            return CheckoutResult(False, str(e))

    def _step_go_to_upgrade(self) -> bool:
        """步骤1: 进入升级页面"""
        logger.info("步骤1: 进入升级页面")
        
        upgrade_selectors = [
            '@@text():Upgrade',
            '@@text():升级',
            '@@text():Upgrade plan',
            '[data-testid="upgrade-button"]',
            'a[href*="upgrade"]',
        ]

        for selector in upgrade_selectors:
            if self.browser.click(selector, timeout=3):
                logger.info("点击升级按钮成功")
                self.browser.human_delay(1, 2)
                return True

        self.browser.goto(self.UPGRADE_URL)
        self.browser.human_delay(1, 2)
        return True

    def _step_select_plan(self) -> bool:
        """步骤2: 选择订阅计划"""
        logger.info("步骤2: 选择订阅计划")
        
        plan_selectors = [
            '@@text():Plus',
            '@@text():Subscribe',
            '@@text():Get Plus',
            '[data-testid="plus-plan"]',
            'button:contains("Plus")',
        ]

        for selector in plan_selectors:
            if self.browser.click(selector, timeout=3):
                logger.info("选择 Plus 计划成功")
                self.browser.human_delay(1, 2)
                return True

        if self.browser.wait_for_url_contains("pay.openai.com", timeout=10):
            return True

        logger.warning("选择订阅计划失败")
        return False

    def _step_fill_payment(self, email: str, card: CardInfo) -> bool:
        """步骤3: 填写支付信息"""
        logger.info("步骤3: 填写支付信息")
        
        if not self.browser.wait_for_url_contains("pay.openai.com", timeout=15):
            logger.warning("未跳转到支付页面")
            return False

        self.browser.human_delay(1, 2)

        self.browser.type_text('#email', email)
        self.browser.human_delay(0.3, 0.5)

        if not self._fill_card_in_iframe(card):
            if not self._fill_card_direct(card):
                logger.warning("填写卡信息失败")
                return False

        self.browser.type_text('#billingName', card.holder_name)
        self.browser.human_delay(0.2, 0.4)

        if card.address_line1:
            self.browser.type_text('#billingAddressLine1', card.address_line1)
        if card.city:
            self.browser.type_text('#billingLocality', card.city)
        if card.state:
            self.browser.type_text('#billingAdministrativeArea', card.state)
        if card.postal_code:
            self.browser.type_text('#billingPostalCode', card.postal_code)

        checkbox = self.browser.find_element('input[type="checkbox"]', timeout=3)
        if checkbox:
            try:
                checkbox.click()
            except Exception:
                pass

        self.browser.human_delay(0.5, 1)
        return True

    def _fill_card_in_iframe(self, card: CardInfo) -> bool:
        """在 Stripe iframe 中填写卡信息"""
        try:
            if not self.browser.page:
                return False
                
            iframe = self.browser.page.ele('iframe[name*="privateStripeFrame"]')
            if not iframe:
                iframe = self.browser.page.ele('iframe[src*="stripe"]')
            
            if not iframe:
                return False

            frame_page = iframe.ele
            if not frame_page:
                return False

            card_input = frame_page.ele('input[name="cardnumber"]')
            if card_input:
                card_input.input(card.card_number)
                time.sleep(0.2)

            expiry_input = frame_page.ele('input[name="exp-date"]')
            if expiry_input:
                expiry_input.input(card.expiry)
                time.sleep(0.2)

            cvc_input = frame_page.ele('input[name="cvc"]')
            if cvc_input:
                cvc_input.input(card.cvv)
                time.sleep(0.2)

            return True
        except Exception as e:
            logger.warning(f"iframe 填写失败: {e}")
            return False

    def _fill_card_direct(self, card: CardInfo) -> bool:
        """直接填写卡信息（非 iframe 情况）"""
        try:
            self.browser.type_text('#cardNumber', card.card_number)
            self.browser.human_delay(0.2, 0.4)

            self.browser.type_text('#cardExpiry', card.expiry)
            self.browser.human_delay(0.2, 0.4)

            self.browser.type_text('#cardCvc', card.cvv)
            self.browser.human_delay(0.2, 0.4)

            return True
        except Exception as e:
            logger.warning(f"直接填写卡信息失败: {e}")
            return False

    def _step_submit_payment(self) -> bool:
        """步骤4: 提交支付"""
        logger.info("步骤4: 提交支付")
        
        submit_selectors = [
            '@@text():Subscribe',
            '@@text():Pay',
            '@@text():订阅',
            '@@text():支付',
            'button[type="submit"]',
            '.SubmitButton',
        ]

        for selector in submit_selectors:
            if self.browser.click(selector, timeout=3):
                logger.info("点击提交按钮成功")
                self.browser.human_delay(2, 4)
                return True

        logger.warning("未找到提交按钮")
        return False

    def _wait_for_success(self, timeout: float = 60) -> bool:
        """等待支付成功"""
        logger.info("等待支付完成...")
        start = time.time()
        while time.time() - start < timeout:
            url = self.browser.current_url()
            
            if "chatgpt.com" in url and "pay" not in url:
                return True
            
            if self.browser.exists('@@text():Payment successful', timeout=1):
                return True
            if self.browser.exists('@@text():Thank you', timeout=1):
                return True
            if self.browser.exists('@@text():Welcome to Plus', timeout=1):
                return True
            
            if self.browser.exists('@@text():Payment failed', timeout=1):
                logger.error("支付失败")
                return False
            if self.browser.exists('@@text():card was declined', timeout=1):
                logger.error("卡被拒绝")
                return False

            time.sleep(2)

        return False
