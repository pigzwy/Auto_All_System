"""
卡池分配服务
"""
from django.db import models, transaction
from django.db.models import Q, F
from django.utils import timezone
from .models import Card, CardUsageLog, CardStatus


class CardAllocationError(Exception):
    """卡分配异常"""
    pass


class CardService:
    """卡池服务"""
    
    @classmethod
    def allocate_card(cls, user=None, pool_type='public', card_type=None, zone=None, lock=False):
        """
        自动分配一张可用卡
        
        Args:
            user: 请求用户（私有卡池需要）
            pool_type: 卡池类型 public/private
            card_type: 卡类型过滤 visa/mastercard
            zone: 专区（用于记录分配来源）
            lock: 是否锁定卡（标记为 in_use），默认 False
        
        Returns:
            Card: 分配的卡对象
        
        Raises:
            CardAllocationError: 无可用卡时抛出
        """
        with transaction.atomic():
            queryset = Card.objects.select_for_update().filter(
                status=CardStatus.AVAILABLE
            )
            
            # 按卡池类型筛选
            if pool_type == 'private' and user:
                queryset = queryset.filter(pool_type='private', owner_user=user)
            else:
                queryset = queryset.filter(pool_type='public')
            
            # 按卡类型筛选
            if card_type:
                queryset = queryset.filter(card_type=card_type)
            
            # 筛选未达使用上限的卡（max_use_count=0 表示无限制）
            queryset = queryset.filter(
                Q(max_use_count=0) | Q(use_count__lt=F('max_use_count'))
            )
            
            # 检查卡密是否过期
            now = timezone.now()
            queryset = queryset.filter(
                Q(key_expire_time__isnull=True) | Q(key_expire_time__gt=now)
            )
            
            # 按使用次数升序，优先分配使用少的
            card = queryset.order_by('use_count', 'created_at').first()
            
            if not card:
                raise CardAllocationError(f'没有可用的{pool_type}卡')
            
            # 仅在需要锁定时才标记为使用中
            if lock:
                card.status = CardStatus.IN_USE
                card.save(update_fields=['status', 'updated_at'])
            
            return card
    
    @classmethod
    def use_card(cls, card, user=None, task=None, purpose='', success=True, 
                 amount=None, currency='USD', error_message='', extra_data=None):
        """
        使用卡并记录日志
        
        Args:
            card: 卡对象
            user: 使用者
            task: 关联任务
            purpose: 用途
            success: 是否成功
            amount: 交易金额
            currency: 货币
            error_message: 错误信息
            extra_data: 额外数据
        
        Returns:
            CardUsageLog: 使用记录
        """
        with transaction.atomic():
            # 更新卡统计
            card.use_count += 1
            if success:
                card.success_count += 1
            card.last_used_at = timezone.now()
            
            # 检查是否达到使用上限
            if card.max_use_count > 0 and card.use_count >= card.max_use_count:
                card.status = CardStatus.USED
            else:
                card.status = CardStatus.AVAILABLE
            
            card.save(update_fields=[
                'use_count', 'success_count', 'last_used_at', 'status', 'updated_at'
            ])
            
            # 创建使用记录
            log = CardUsageLog.objects.create(
                card=card,
                user=user,
                task=task,
                purpose=purpose,
                success=success,
                error_message=error_message,
                amount=amount,
                currency=currency,
                extra_data=extra_data or {}
            )
            
            return log
    
    @classmethod
    def release_card(cls, card):
        """
        释放卡（任务取消时调用）
        不增加使用次数，仅恢复状态
        """
        if card.status == CardStatus.IN_USE:
            # 检查是否还有使用额度
            if card.max_use_count > 0 and card.use_count >= card.max_use_count:
                card.status = CardStatus.USED
            else:
                card.status = CardStatus.AVAILABLE
            card.save(update_fields=['status', 'updated_at'])
    
    @classmethod
    def get_card_with_info(cls, card):
        """
        获取卡完整信息（用于支付）
        
        Returns:
            dict: 包含卡号、CVV、有效期、账单地址等
        """
        return {
            'card_number': card.card_number,
            'cvv': card.cvv,
            'exp_month': str(card.expiry_month).zfill(2),
            'exp_year': str(card.expiry_year),
            'card_holder': card.card_holder or '',
            'card_type': card.card_type,
            'billing_address': card.billing_address or {}
        }
