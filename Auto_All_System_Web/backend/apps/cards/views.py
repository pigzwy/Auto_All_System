"""
虚拟卡视图
"""
import requests
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .models import Card, CardUsageLog, CardPoolType, CardApiConfig
from .serializers import CardSerializer, CardUsageLogSerializer, CardImportSerializer, CardApiConfigSerializer

logger = logging.getLogger(__name__)


class CardViewSet(viewsets.ModelViewSet):
    """虚拟卡API"""
    
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'pool_type', 'owner_user']
    
    def get_queryset(self):
        """
        权限控制：
        1. 超级管理员可以看到所有卡
        2. 普通管理员/用户只能看到公共卡池的卡和自己的私有卡
        """
        user = self.request.user
        
        # 超级管理员能看到所有卡
        if user.is_superuser:
            return Card.objects.all().select_related('owner_user')
        
        # 普通用户/普通管理员：公共卡池 + 自己的私有卡
        return Card.objects.filter(
            models.Q(pool_type=CardPoolType.PUBLIC) |
            models.Q(owner_user=user)
        ).select_related('owner_user')
    
    def perform_create(self, serializer):
        """创建虚拟卡"""
        # 如果是私有卡，自动设置所有者
        if serializer.validated_data.get('pool_type') == CardPoolType.PRIVATE:
            serializer.save(owner_user=self.request.user)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """获取可用的虚拟卡列表"""
        cards = self.filter_queryset(self.get_queryset()).filter(status='available')
        
        page = self.paginate_queryset(cards)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(cards, many=True)
        return Response({
            'code': 200,
            'message': 'Success',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def my_cards(self, request):
        """获取我的私有卡"""
        cards = Card.objects.filter(owner_user=request.user)
        
        serializer = self.get_serializer(cards, many=True)
        return Response({
            'code': 200,
            'message': 'Success',
            'data': {
                'cards': serializer.data,
                'statistics': {
                    'total': cards.count(),
                    'available': cards.filter(status='available').count(),
                    'used': cards.filter(status='used').count(),
                }
            }
        })
    
    @action(detail=False, methods=['post'])
    def import_cards(self, request):
        """批量导入虚拟卡"""
        serializer = CardImportSerializer(data=request.data)
        
        if serializer.is_valid():
            cards_data = serializer.validated_data['cards_data']
            pool_type = serializer.validated_data['pool_type']
            
            success_count = 0
            failed_count = 0
            errors = []
            
            for card_data in cards_data:
                try:
                    # 自动识别卡类型
                    card_number = card_data['card_number']
                    card_type = card_data.get('card_type')
                    if not card_type or card_type == 'visa': # 默认或没传时自动识别
                        if card_number.startswith('4'):
                            card_type = 'visa'
                        elif card_number.startswith('5'):
                            card_type = 'mastercard'
                        else:
                            card_type = card_data.get('card_type', 'other')

                    Card.objects.create(
                        card_number=card_number,
                        card_holder=card_data.get('card_holder', ''),
                        expiry_month=card_data['expiry_month'],
                        expiry_year=card_data['expiry_year'],
                        cvv=card_data['cvv'],
                        card_type=card_type,
                        bank_name=card_data.get('bank_name', ''),
                        billing_address=card_data.get('billing_address', {}),
                        balance=card_data.get('balance', 0.00),
                        pool_type=pool_type,
                        owner_user=request.user if pool_type == 'private' else None,
                        status='available',
                        notes=card_data.get('notes', '')
                    )
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append({
                        'card_number': card_data.get('card_number', 'unknown'),
                        'error': str(e)
                    })
            
            return Response({
                'code': 200,
                'message': '导入完成',
                'data': {
                    'success': success_count,
                    'failed': failed_count,
                    'total': len(cards_data),
                    'errors': errors
                }
            })
        
        return Response({
            'code': 400,
            'message': '导入失败',
            'data': {
                'errors': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def redeem_card(self, request):
        """
        通过卡密查询并导入卡信息
        使用可配置的外部 API（query 接口）
        """
        key_id = request.data.get('key_id')
        pool_type = request.data.get('pool_type', 'public')
        config_id = request.data.get('config_id')
        
        if not key_id:
            return Response({
                'code': 400,
                'message': '缺少卡密参数 key_id',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取 API 配置
        if config_id:
            api_config = CardApiConfig.objects.filter(id=config_id, is_active=True).first()
        else:
            api_config = CardApiConfig.get_default()
        
        if not api_config:
            return Response({
                'code': 400,
                'message': '没有可用的 API 配置，请先在系统设置中添加',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 激活操作优先使用 redeem_url，query_url 仅用于查询
            api_url = api_config.redeem_url or api_config.query_url
            if not api_url:
                return Response({
                    'code': 400,
                    'message': 'API 配置缺少接口 URL',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 构建请求体
            request_body = {'key_id': key_id}
            if api_config.request_body_template:
                import json
                template = json.dumps(api_config.request_body_template)
                template = template.replace('{key_id}', key_id)
                request_body = json.loads(template)
            
            # 构建请求头
            headers = {'Content-Type': 'application/json'}
            if api_config.request_headers:
                headers.update(api_config.request_headers)
            
            # 调用外部 API
            response = requests.request(
                method=api_config.request_method,
                url=api_url,
                json=request_body,
                headers=headers,
                timeout=api_config.timeout
            )
            
            if response.status_code != 200:
                return Response({
                    'code': response.status_code,
                    'message': f'查询失败: {response.text}',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = response.json()

            # 检查是否成功；如果激活接口返回"已被使用"，回退到 query_url 查询
            if not result.get('success', False):
                error_msg = str(result.get('error', '') or result.get('message', '') or 'API 返回失败')
                # 如果是 redeem_url 返回已被使用，且有 query_url 可用，则回退查询
                query_url = api_config.query_url
                if query_url and api_url != query_url:
                    try:
                        query_body = {'key_id': key_id}
                        if api_config.request_body_template:
                            import json as _json
                            _tpl = _json.dumps(api_config.request_body_template)
                            _tpl = _tpl.replace('{key_id}', key_id)
                            query_body = _json.loads(_tpl)
                        query_resp = requests.request(
                            method=api_config.request_method,
                            url=query_url,
                            json=query_body,
                            headers=headers,
                            timeout=api_config.timeout,
                        )
                        if query_resp.status_code == 200:
                            query_result = query_resp.json()
                            if query_result.get('success', False) and query_result.get('card'):
                                result = query_result
                            else:
                                return Response({
                                    'code': 400,
                                    'message': f'激活失败: {error_msg}',
                                    'data': result
                                }, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response({
                                'code': 400,
                                'message': f'激活失败: {error_msg}',
                                'data': result
                            }, status=status.HTTP_400_BAD_REQUEST)
                    except Exception:
                        return Response({
                            'code': 400,
                            'message': f'激活失败: {error_msg}',
                            'data': result
                        }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({
                        'code': 400,
                        'message': f'激活失败: {error_msg}',
                        'data': result
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # 检查卡是否已销毁
            if result.get('destroyed', False):
                return Response({
                    'code': 400,
                    'message': '该卡已被销毁，无法使用',
                    'data': {
                        'destroyed': True,
                        'destroyed_time': result.get('destroyed_time')
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 提取 expire_time（用于存入 key_expire_time，不阻止激活）
            from django.utils import timezone
            from datetime import datetime
            expire_time_str = result.get('card', {}).get('expire_time')

            # 检查卡的信用卡有效期（exp_month/exp_year）是否已过期
            card_data_check = result.get('card', {})
            field_map_check = (api_config.response_mapping or {}).get('fields', {})
            check_exp_month = card_data_check.get(field_map_check.get('exp_month', 'exp_month'))
            check_exp_year = card_data_check.get(field_map_check.get('exp_year', 'exp_year'))
            if check_exp_month and check_exp_year:
                try:
                    ey = int(check_exp_year)
                    em = int(check_exp_month)
                    if ey < 100:
                        ey += 2000
                    now = timezone.now()
                    if now.year > ey or (now.year == ey and now.month > em):
                        return Response({
                            'code': 400,
                            'message': '该卡已过期，无法使用',
                            'data': {
                                'expired': True,
                                'expiry': f'{em:02d}/{ey}'
                            }
                        }, status=status.HTTP_400_BAD_REQUEST)
                except (ValueError, TypeError):
                    pass
            
            # 使用字段映射解析响应
            mapping = api_config.response_mapping or {}
            
            # 获取 card 和 legal_address 数据
            card_path = mapping.get('card_path', 'card')
            address_path = mapping.get('address_path', 'legal_address')
            
            card_data = result.get(card_path, {})
            address_data = result.get(address_path, {})
            
            if not card_data:
                return Response({
                    'code': 400,
                    'message': '激活失败: 无效的响应格式',
                    'data': result
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 字段映射（支持自定义，默认兼容实际 API 格式）
            field_map = mapping.get('fields', {})
            
            # 解析卡信息
            card_number = str(card_data.get(field_map.get('pan', 'pan'), ''))
            card_cvc = str(card_data.get(field_map.get('cvv', 'cvv'), ''))
            exp_month = card_data.get(field_map.get('exp_month', 'exp_month'), '01')
            exp_year = card_data.get(field_map.get('exp_year', 'exp_year'), '2025')
            
            # 解析过期时间
            expiry_month = int(exp_month) if exp_month else 1
            expiry_year = int(exp_year) if exp_year else 2025
            if expiry_year < 100:
                expiry_year += 2000
            
            # 解析账单地址
            billing_address = {
                'address_line1': address_data.get(field_map.get('address1', 'address1'), ''),
                'address_line2': address_data.get(field_map.get('address2', 'address2'), ''),
                'city': address_data.get(field_map.get('city', 'city'), ''),
                'state': address_data.get(field_map.get('region', 'region'), ''),
                'postal_code': address_data.get(field_map.get('postal_code', 'postal_code'), ''),
                'country': address_data.get(field_map.get('country', 'country'), 'US'),
            }
            
            # 解析持卡人姓名：优先 legal_address 中的 first_name + last_name，兜底 card_holder
            first_name = str(address_data.get(field_map.get('first_name', 'first_name'), '') or '').strip()
            last_name = str(address_data.get(field_map.get('last_name', 'last_name'), '') or '').strip()
            card_holder_name = f"{first_name} {last_name}".strip()
            if not card_holder_name:
                card_holder_name = str(card_data.get('card_holder', '') or card_data.get('cardholder_name', '') or '').strip()
            if not card_holder_name:
                card_holder_name = str(address_data.get('name', '') or '').strip()
            
            # 解析卡密过期时间
            key_expire_time = None
            if expire_time_str:
                try:
                    key_expire_time = datetime.fromisoformat(expire_time_str.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    pass

            # 检查卡密是否已过期（expire_time 是卡密有效期，不是信用卡有效期）
            if key_expire_time and timezone.now() >= key_expire_time:
                return Response({
                    'code': 400,
                    'message': f'该卡密已过期（{key_expire_time.strftime("%Y-%m-%d %H:%M")}），无法使用',
                    'data': {
                        'key_expired': True,
                        'key_expire_time': expire_time_str,
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 自动识别卡类型
            card_type = 'other'
            if card_number.startswith('4'):
                card_type = 'visa'
            elif card_number.startswith('5'):
                card_type = 'mastercard'
            elif card_number.startswith('3'):
                card_type = 'amex'
            
            # 检查本地是否已有同卡号记录（避免重复导入）
            existing = Card.objects.filter(card_number=card_number).first()
            if existing:
                # 更新已有记录的信息（可能之前导入时信息不完整）
                existing.card_holder = card_holder_name or existing.card_holder
                existing.cvv = card_cvc or existing.cvv
                existing.expiry_month = expiry_month
                existing.expiry_year = expiry_year
                existing.billing_address = billing_address or existing.billing_address
                existing.key_expire_time = key_expire_time or existing.key_expire_time
                if existing.status in ('in_use', 'expired', 'disabled'):
                    existing.status = 'available'
                existing.save()
                serializer = self.get_serializer(existing)
                return Response({
                    'code': 200,
                    'message': '该卡已存在，已更新信息',
                    'data': serializer.data
                })

            # 创建卡记录
            card = Card.objects.create(
                card_number=card_number,
                card_holder=card_holder_name,
                expiry_month=expiry_month,
                expiry_year=expiry_year,
                cvv=card_cvc,
                card_type=card_type,
                pool_type=pool_type,
                owner_user=request.user if pool_type == 'private' else None,
                status='available',
                billing_address=billing_address,
                key_expire_time=key_expire_time,
                notes=f'通过 {api_config.name} 导入: {key_id[:8]}...'
            )
            
            serializer = self.get_serializer(card)
            
            return Response({
                'code': 200,
                'message': '激活成功',
                'data': serializer.data
            })
            
        except requests.Timeout:
            logger.error(f'Redeem card timeout: key_id={key_id}, config={api_config.name}')
            return Response({
                'code': 500,
                'message': '激活超时，请稍后重试',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except requests.RequestException as e:
            logger.error(f'Redeem card request error: {e}')
            return Response({
                'code': 500,
                'message': f'网络请求失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f'Redeem card error: {e}')
            return Response({
                'code': 500,
                'message': f'激活失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def query_card(self, request):
        """
        查询卡密信息（不激活）
        使用可配置的外部 API
        """
        key_id = request.data.get('key_id')
        config_id = request.data.get('config_id')
        
        if not key_id:
            return Response({
                'code': 400,
                'message': '缺少卡密参数 key_id',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取 API 配置
        if config_id:
            api_config = CardApiConfig.objects.filter(id=config_id, is_active=True).first()
        else:
            api_config = CardApiConfig.get_default()
        
        if not api_config or not api_config.query_url:
            return Response({
                'code': 400,
                'message': '没有可用的查询 API 配置',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            headers = {'Content-Type': 'application/json'}
            if api_config.request_headers:
                headers.update(api_config.request_headers)
            
            response = requests.request(
                method=api_config.request_method,
                url=api_config.query_url,
                json={'key_id': key_id},
                headers=headers,
                timeout=api_config.timeout
            )
            
            if response.status_code != 200:
                return Response({
                    'code': response.status_code,
                    'message': f'查询失败: {response.text}',
                    'data': None
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = response.json()
            
            return Response({
                'code': 200,
                'message': '查询成功',
                'data': result
            })
            
        except requests.Timeout:
            return Response({
                'code': 500,
                'message': '查询超时',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'code': 500,
                'message': f'查询失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CardUsageLogViewSet(viewsets.ReadOnlyModelViewSet):
    """卡使用记录API"""
    
    queryset = CardUsageLog.objects.all()
    serializer_class = CardUsageLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """用户只能查看自己的使用记录"""
        if self.request.user.is_staff:
            return CardUsageLog.objects.all()
        return CardUsageLog.objects.filter(user=self.request.user)


class CardApiConfigViewSet(viewsets.ModelViewSet):
    """卡密API配置管理"""
    
    queryset = CardApiConfig.objects.all()
    serializer_class = CardApiConfigSerializer
    permission_classes = [permissions.IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def active_list(self, request):
        """获取所有启用的配置（供激活对话框选择）"""
        configs = CardApiConfig.objects.filter(is_active=True)
        serializer = self.get_serializer(configs, many=True)
        return Response({
            'code': 200,
            'message': 'Success',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设置为默认配置"""
        config = self.get_object()
        config.is_default = True
        config.save()
        return Response({
            'code': 200,
            'message': f'{config.name} 已设为默认',
            'data': self.get_serializer(config).data
        })
