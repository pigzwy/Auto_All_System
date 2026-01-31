<template>
  <div class="space-y-6">
    <Card class="bg-card text-card-foreground text-center py-6">
      <CardHeader>
        <CardTitle class="text-3xl">👑 VIP会员</CardTitle>
        <CardDescription class="text-base">升级VIP，享受专属特权</CardDescription>
      </CardHeader>
    </Card>

    <!-- 当前会员状态 -->
    <Card v-if="userVip.level > 0" class="bg-gradient-to-br from-indigo-500 to-purple-600 text-white border-none shadow-lg">
      <CardContent class="flex items-center gap-6 p-6">
        <div class="flex flex-col items-center gap-2">
          <span class="text-5xl">👑</span>
          <span class="text-2xl font-bold">VIP {{ userVip.level }}</span>
        </div>
        <div class="flex-1 space-y-3">
          <div class="text-lg">到期时间: {{ userVip.expire_date }}</div>
          <div class="space-y-1">
            <div class="flex justify-between text-sm opacity-90">
              <span>进度</span>
              <span>剩余{{ remainingDays }}天</span>
            </div>
            <Progress :model-value="daysProgress" class="h-2 bg-white/20" />
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- VIP套餐 -->
    <div class="grid gap-6 md:grid-cols-3">
      <Card
        v-for="plan in vipPlans"
        :key="plan.level"
        class="relative flex flex-col transition-all hover:-translate-y-2 hover:shadow-lg"
        :class="{
          'border-primary shadow-md': plan.recommended,
          'border-emerald-500': userVip.level === plan.level
        }"
      >
        <div v-if="plan.recommended" class="absolute top-3 right-3 rounded-full bg-primary px-3 py-1 text-xs font-bold text-primary-foreground">
          🔥 推荐
        </div>
        <div v-if="userVip.level === plan.level" class="absolute top-3 right-3 rounded-full bg-emerald-500 px-3 py-1 text-xs font-bold text-white">
          ✓ 当前
        </div>

        <CardHeader class="text-center pb-2">
          <div class="text-6xl mb-4">{{ plan.icon }}</div>
          <CardTitle class="text-2xl">{{ plan.name }}</CardTitle>
          <div class="flex items-baseline justify-center gap-1 mt-2">
            <span class="text-3xl font-bold text-primary">¥{{ plan.price }}</span>
            <span class="text-muted-foreground">/{{ plan.period }}</span>
          </div>
        </CardHeader>

        <CardContent class="flex-1">
          <div class="space-y-3">
            <div v-for="feature in plan.features" :key="feature" class="flex items-center gap-2 text-sm">
              <Check class="h-4 w-4 text-emerald-500 shrink-0" />
              <span>{{ feature }}</span>
            </div>
          </div>
        </CardContent>

        <CardFooter>
          <Button
            :variant="plan.recommended ? 'default' : 'outline'"
            size="lg"
            class="w-full"
            :disabled="userVip.level >= plan.level"
            @click="handleSubscribe(plan)"
          >
            {{ userVip.level >= plan.level ? '已订阅' : '立即订阅' }}
          </Button>
        </CardFooter>
      </Card>
    </div>

    <!-- VIP特权说明 -->
    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>VIP特权详细说明</CardTitle>
      </CardHeader>
      <CardContent>
        <Accordion type="single" collapsible class="w-full">
          <AccordionItem value="item-1">
            <AccordionTrigger>🚀 任务优先执行</AccordionTrigger>
            <AccordionContent>VIP用户的任务将获得更高的执行优先级，更快完成任务</AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-2">
            <AccordionTrigger>💎 专属浏览器配置</AccordionTrigger>
            <AccordionContent>获得性能更好、稳定性更高的浏览器实例配置</AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-3">
            <AccordionTrigger>📊 更多并发任务</AccordionTrigger>
            <AccordionContent>可以同时运行更多数量的任务，提升工作效率</AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-4">
            <AccordionTrigger>🎁 每日任务奖励</AccordionTrigger>
            <AccordionContent>完成每日任务可获得额外奖励金币</AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-5">
            <AccordionTrigger>👨‍💼 专属客服支持</AccordionTrigger>
            <AccordionContent>享受一对一专属客服支持，问题快速响应</AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-6">
            <AccordionTrigger>💰 充值优惠折扣</AccordionTrigger>
            <AccordionContent>充值时可享受专属折扣优惠</AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from '@/lib/element'
import { Check } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

const userVip = ref({
  level: 1,
  expire_date: '2024-03-15',
  start_date: '2024-01-15'
})

const vipPlans = [
  {
    level: 1,
    name: 'VIP 1',
    icon: '🥉',
    price: 29,
    period: '月',
    recommended: false,
    features: [
      '任务优先执行',
      '同时3个任务',
      '标准客服支持',
      '基础数据统计'
    ]
  },
  {
    level: 2,
    name: 'VIP 2',
    icon: '🥈',
    price: 79,
    period: '月',
    recommended: true,
    features: [
      '任务高优先级',
      '同时10个任务',
      '专属浏览器配置',
      '每日任务奖励',
      '优先客服支持',
      '高级数据分析'
    ]
  },
  {
    level: 3,
    name: 'VIP 3',
    icon: '🥇',
    price: 199,
    period: '月',
    recommended: false,
    features: [
      '任务最高优先级',
      '无限并发任务',
      '专属高性能配置',
      '双倍任务奖励',
      '1对1专属客服',
      '充值9折优惠',
      '全部高级功能'
    ]
  }
]

const remainingDays = computed(() => {
  const expire = new Date(userVip.value.expire_date)
  const today = new Date()
  const diff = expire.getTime() - today.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
})

const daysProgress = computed(() => {
  const start = new Date(userVip.value.start_date)
  const expire = new Date(userVip.value.expire_date)
  const today = new Date()
  const total = expire.getTime() - start.getTime()
  const used = today.getTime() - start.getTime()
  return Math.max(0, Math.min(100, (used / total) * 100))
})

const handleSubscribe = (plan: any) => {
  ElMessage.success(`准备订阅 ${plan.name}，价格: ¥${plan.price}`)
  // TODO: 调用订阅API
}
</script>
