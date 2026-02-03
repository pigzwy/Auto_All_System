<template>
  <div class="space-y-6">
    <Card class="bg-gradient-to-br from-background to-muted/20 text-card-foreground shadow-sm border-border/80">
      <CardHeader>
        <CardTitle class="text-3xl">💰 账户充值</CardTitle>
        <CardDescription class="text-base flex items-center gap-2">
          当前余额: <span class="text-emerald-600 font-bold text-xl">¥{{ balance }}</span>
        </CardDescription>
      </CardHeader>
    </Card>

    <div class="grid gap-6 md:grid-cols-3">
      <div class="md:col-span-2 space-y-6">
        <Card class="bg-card text-card-foreground shadow-sm border-border/80">
          <CardHeader>
            <CardTitle>充值金额</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="grid grid-cols-3 gap-4">
              <div
                v-for="amount in amountOptions"
                :key="amount"
                class="relative flex flex-col items-center justify-center rounded-2xl border-2 bg-background/70 p-6 transition-all hover:-translate-y-1 hover:shadow-md cursor-pointer"
                :class="selectedAmount === amount ? 'border-primary bg-primary/5 shadow-md' : 'border-border hover:border-primary/50 hover:bg-primary/5'"
                @click="selectedAmount = amount; customAmount = undefined"
              >
                <div class="text-2xl font-bold">¥{{ amount }}</div>
                <div class="text-xs text-amber-500 font-medium mt-1" v-if="getBonus(amount)">
                  送 ¥{{ getBonus(amount) }}
                </div>
              </div>
            </div>

            <div class="mt-6">
              <label class="text-sm font-medium mb-2 block">自定义金额</label>
              <div class="relative">
                <span class="absolute left-3 top-2.5 text-muted-foreground">¥</span>
                <Input
                  v-model.number="customAmount"
                  type="number"
                  placeholder="请输入充值金额"
                  class="pl-8"
                  @focus="selectedAmount = 0"
                />
              </div>
            </div>

            <div class="mt-8">
              <h3 class="text-lg font-semibold mb-4">支付方式</h3>
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div
                  v-for="method in availablePaymentMethods"
                  :key="method.gateway"
                  class="flex flex-col items-center justify-center rounded-xl border-2 bg-background/70 p-4 transition-all hover:-translate-y-0.5 hover:shadow-sm cursor-pointer"
                  :class="selectedPayment === method.gateway ? 'border-primary bg-primary/5 shadow-sm' : 'border-border hover:border-primary/50 hover:bg-primary/5'"
                  @click="selectedPayment = method.gateway"
                >
                  <div class="text-3xl mb-2">{{ method.icon }}</div>
                  <div class="text-sm font-medium">{{ method.name }}</div>
                </div>
              </div>
            </div>

            <div v-if="selectedPayment === 'card_code'" class="mt-6 rounded-xl border border-border/80 bg-gradient-to-br from-muted/30 via-background to-muted/10 p-4">
              <div class="space-y-2">
                <label class="text-sm font-medium">充值卡密</label>
                <div class="relative">
                  <span class="absolute left-3 top-2.5">🎫</span>
                  <Input
                    v-model="cardCode"
                    placeholder="请输入卡密，格式: XXXX-XXXX-XXXX-XXXX"
                    class="pl-9"
                  />
                </div>
              </div>
              <Alert class="mt-4">
                <AlertTitle>提示</AlertTitle>
                <AlertDescription>使用卡密充值将忽略上方选择的金额，按卡密面值充值</AlertDescription>
              </Alert>
            </div>
          </CardContent>
        </Card>
      </div>

      <div class="space-y-6">
        <Card class="bg-gradient-to-br from-background to-muted/20 text-card-foreground shadow-sm border-border/80">
          <CardHeader>
            <CardTitle>订单信息</CardTitle>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">充值金额</span>
              <span class="font-bold">¥{{ finalAmount }}</span>
            </div>
            <div class="flex justify-between text-sm" v-if="bonusAmount > 0">
              <span class="text-muted-foreground">赠送金额</span>
              <span class="font-bold text-emerald-600">+¥{{ bonusAmount }}</span>
            </div>
            <div class="h-px bg-border my-2"></div>
            <div class="flex justify-between items-end">
              <span class="text-lg font-semibold">实际到账</span>
              <span class="text-2xl font-bold text-primary">¥{{ totalAmount }}</span>
            </div>

            <Button
              size="lg"
              class="mt-4 h-11 w-full"
              :disabled="!canSubmit"
              @click="handleRecharge"
            >
              <Loader2 v-if="loading" class="mr-2 h-4 w-4 animate-spin" />
              立即充值
            </Button>

            <div class="mt-6 rounded-xl border border-amber-500/20 bg-amber-500/10 p-4">
              <div class="flex gap-2">
                <Info class="h-5 w-5 text-amber-600 shrink-0" />
                <div>
                  <p class="text-sm font-semibold text-amber-700 mb-1">充值说明：</p>
                  <ul class="text-xs text-amber-700/80 list-disc pl-4 space-y-1">
                    <li>充值后立即到账</li>
                    <li>单笔最低充值10元</li>
                    <li>充值金额不可退款</li>
                    <li>遇到问题请联系客服</li>
                  </ul>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card class="bg-card text-card-foreground shadow-sm border-border/80">
          <CardHeader>
            <CardTitle>充值记录</CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="rechargeHistory.length > 0" class="space-y-6 relative pl-4 border-l border-border ml-2">
              <div v-for="record in rechargeHistory" :key="record.id" class="relative pl-6">
                <div class="absolute -left-[21px] top-1 h-3 w-3 rounded-full border-2 border-primary bg-background"></div>
                <div class="text-sm text-muted-foreground mb-1">{{ formatDate(record.created_at) }}</div>
                <div class="flex items-center justify-between rounded-lg border border-border bg-background/70 p-3 shadow-sm">
                  <span class="font-medium">充值 ¥{{ record.amount }}</span>
                  <Badge variant="default" class="bg-emerald-600 hover:bg-emerald-700">已完成</Badge>
                </div>
              </div>
            </div>
            <div v-else class="py-8 text-center text-sm text-muted-foreground">暂无充值记录</div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { Info, Loader2 } from 'lucide-vue-next'
import { balanceApi, type BalanceLog } from '@/api/balance'
import { paymentsApi, type PaymentConfig } from '@/api/payments'
import type { UserBalance } from '@/types'
import dayjs from 'dayjs'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const balance = ref('0.00')
const selectedAmount = ref(0)
const customAmount = ref<number>()
const selectedPayment = ref('')
const loading = ref(false)
const cardCode = ref('')
const availablePaymentMethods = ref<PaymentConfig[]>([])

const amountOptions = [10, 50, 100, 200, 500, 1000]

const rechargeHistory = ref<BalanceLog[]>([])

// 获取余额
const fetchBalance = async () => {
  try {
    const data: UserBalance = await balanceApi.getMyBalance()
    balance.value = data.balance
  } catch (error) {
    console.error('Failed to fetch balance:', error)
    ElMessage.error('获取余额失败')
  }
}

// 获取充值记录
const fetchRechargeHistory = async () => {
  try {
    const response = await balanceApi.getBalanceLogs({ 
      transaction_type: 'recharge',
      page_size: 5 
    })
    rechargeHistory.value = response.results
  } catch (error) {
    console.error('Failed to fetch recharge history:', error)
  }
}

// 获取启用的支付方式
const fetchPaymentMethods = async () => {
  try {
    const methods = await paymentsApi.getEnabledPaymentMethods()
    availablePaymentMethods.value = methods
    // 默认选中第一个启用的支付方式
    if (methods.length > 0) {
      selectedPayment.value = methods[0].gateway
    }
  } catch (error) {
    console.error('Failed to fetch payment methods:', error)
  }
}

const getBonus = (amount: number) => {
  if (amount >= 1000) return 100
  if (amount >= 500) return 30
  if (amount >= 200) return 10
  return 0
}

const finalAmount = computed(() => {
  return selectedAmount.value || customAmount.value || 0
})

const bonusAmount = computed(() => {
  return getBonus(finalAmount.value)
})

const totalAmount = computed(() => {
  return finalAmount.value + bonusAmount.value
})

const canSubmit = computed(() => {
  if (loading.value) return false
  
  // 卡密充值
  if (selectedPayment.value === 'card_code') {
    return cardCode.value.length > 0
  }
  
  // 普通充值
  return finalAmount.value >= 10 && selectedPayment.value
})

const handleRecharge = async () => {
  // 卡密充值
  if (selectedPayment.value === 'card_code') {
    if (!cardCode.value) {
      ElMessage.warning('请输入卡密')
      return
    }
    
    loading.value = true
    try {
      const result = await paymentsApi.useCardCode({ card_code: cardCode.value })
      ElMessage.success(result.message || '卡密充值成功！')
      
      // 刷新余额和充值记录
      await fetchBalance()
      await fetchRechargeHistory()
      
      // 重置表单
      cardCode.value = ''
    } catch (error: any) {
      console.error('Failed to use card code:', error)
      ElMessage.error(error?.response?.data?.message || '卡密无效或已使用')
    } finally {
      loading.value = false
    }
    return
  }
  
  // 普通充值
  if (finalAmount.value < 10) {
    ElMessage.warning('单笔最低充值10元')
    return
  }

  loading.value = true
  try {
    await balanceApi.recharge({
      amount: finalAmount.value
    })
    ElMessage.success('充值成功！')
    
    // 刷新余额和充值记录
    await fetchBalance()
    await fetchRechargeHistory()
    
    // 重置表单
    selectedAmount.value = 0
    customAmount.value = undefined
  } catch (error) {
    console.error('Failed to recharge:', error)
    ElMessage.error('充值失败，请重试')
  } finally {
    loading.value = false
  }
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

// 组件挂载时获取数据
onMounted(() => {
  fetchBalance()
  fetchRechargeHistory()
  fetchPaymentMethods()
})
</script>
