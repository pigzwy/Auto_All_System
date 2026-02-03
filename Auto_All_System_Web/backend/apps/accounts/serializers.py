"""
用户账户序列化器
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import UserBalance, BalanceLog

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""

    is_staff = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'avatar',
            'role', 'is_active', 'is_verified', 'is_staff', 'is_superuser',
            'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'role', 'is_staff', 'is_superuser', 'created_at', 'last_login']

    def get_is_staff(self, obj):
        return bool(obj.is_staff or obj.is_admin or obj.is_superuser)


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'phone']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "两次密码不一致"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(
                request=self.context.get('request'),
                username=username,
                password=password
            )
            
            if not user:
                raise serializers.ValidationError('用户名或密码错误')
            
            if not user.is_active:
                raise serializers.ValidationError('用户已被禁用')
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('必须提供用户名和密码')


class ChangePasswordSerializer(serializers.Serializer):
    """用户自助修改密码"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.check_password(value):
            raise serializers.ValidationError('旧密码不正确')
        return value

    def validate_new_password(self, value):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        try:
            validate_password(value, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class UserBalanceSerializer(serializers.ModelSerializer):
    """用户余额序列化器"""
    
    available_balance = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    user_info = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = UserBalance
        fields = [
            'id', 'user', 'user_info', 'balance', 'currency',
            'frozen_amount', 'available_balance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class BalanceLogSerializer(serializers.ModelSerializer):
    """余额变动记录序列化器"""
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = BalanceLog
        fields = [
            'id', 'user', 'amount', 'balance_before', 'balance_after',
            'type', 'type_display', 'description',
            'related_order_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RechargeSerializer(serializers.Serializer):
    """充值序列化器"""
    
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=1,
        help_text='充值金额（元）'
    )
    payment_method = serializers.ChoiceField(
        choices=['alipay', 'wechat', 'stripe'],
        default='alipay',
        help_text='支付方式'
    )
