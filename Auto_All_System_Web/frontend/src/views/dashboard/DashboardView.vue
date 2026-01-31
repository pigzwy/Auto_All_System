<template>
  <div class="space-y-6">
    <!-- 顶部欢迎栏 -->
    <Card class="relative overflow-hidden">
      <CardContent class="flex items-center justify-between p-6">
        <div class="relative z-10">
          <h1 class="mb-2 text-2xl font-semibold text-card-foreground">
            早安, {{ userStore.user?.username || '用户' }} 👋
          </h1>
          <p class="text-sm text-muted-foreground">
            这里是您的自动化控制中心，今日系统运行正常。
          </p>
        </div>
        <!-- 装饰背景 -->
        <div class="pointer-events-none absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-primary/10 to-transparent" />
      </CardContent>
    </Card>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- 余额卡片 -->
      <Card class="relative overflow-hidden transition-shadow duration-300 hover:shadow-md">
        <CardContent class="p-6">
          <div class="mb-4 flex items-center justify-between">
            <span class="text-sm font-medium text-muted-foreground">账户余额</span>
            <div class="rounded-lg bg-primary/10 p-2 text-primary transition-transform group-hover:scale-110">
              <Icon :size="20"><Wallet /></Icon>
            </div>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-3xl font-bold text-card-foreground">¥{{ balance?.balance || '0.00' }}</span>
            <span class="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-600">
              <Icon><Top /></Icon> 正常
            </span>
          </div>
          <div class="mt-4 flex gap-2 border-t border-border/60 pt-4">
            <button
              @click="$router.push('/recharge')"
              class="flex-1 rounded-md bg-secondary py-1.5 text-xs text-secondary-foreground transition-colors hover:bg-secondary/80"
            >
              充值
            </button>
            <button
              @click="$router.push('/balance')"
              class="flex-1 rounded-md bg-secondary py-1.5 text-xs text-secondary-foreground transition-colors hover:bg-secondary/80"
            >
              明细
            </button>
          </div>
        </CardContent>
      </Card>

      <!-- 专区卡片 -->
      <Card class="transition-shadow duration-300 hover:shadow-md">
        <CardContent class="p-6">
          <div class="mb-4 flex items-center justify-between">
            <span class="text-sm font-medium text-muted-foreground">可用专区</span>
            <div class="rounded-lg bg-amber-500/10 p-2 text-amber-600 transition-transform group-hover:scale-110">
              <Icon :size="20"><Grid /></Icon>
            </div>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-3xl font-bold text-card-foreground">{{ zones.length || 0 }}</span>
            <span class="text-sm text-muted-foreground">个活跃环境</span>
          </div>
          <div class="mt-4 border-t border-border/60 pt-4 text-xs text-muted-foreground">
            最近访问: {{ zones[0]?.name || '无' }}
          </div>
        </CardContent>
      </Card>

      <!-- 虚拟卡卡片 -->
      <Card class="transition-shadow duration-300 hover:shadow-md">
        <CardContent class="p-6">
          <div class="mb-4 flex items-center justify-between">
            <span class="text-sm font-medium text-muted-foreground">虚拟卡资源</span>
            <div class="rounded-lg bg-destructive/10 p-2 text-destructive transition-transform group-hover:scale-110">
              <Icon :size="20"><CreditCard /></Icon>
            </div>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-3xl font-bold text-card-foreground">{{ cardCount || 0 }}</span>
            <span class="text-sm text-muted-foreground">张可用</span>
          </div>
          <div class="mt-4 border-t border-border/60 pt-4">
            <div class="mb-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div class="h-1.5 w-[70%] rounded-full bg-destructive" />
            </div>
            <div class="flex justify-between text-xs text-muted-foreground">
              <span>使用率</span>
              <span>70%</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 快速操作区 -->
    <Card>
      <CardHeader>
        <div class="flex items-center gap-2">
          <span class="h-6 w-1 rounded-full bg-primary" />
          <CardTitle class="text-lg">快速操作</CardTitle>
        </div>
      </CardHeader>

      <CardContent>
        <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div @click="$router.push('/zones')" class="group cursor-pointer p-4 rounded-xl border border-border hover:border-primary/30 hover:bg-primary/5 transition-all duration-300 flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            <Icon :size="24"><Grid /></Icon>
          </div>
          <span class="text-sm font-medium text-card-foreground group-hover:text-primary">浏览专区</span>
        </div>

        <div @click="$router.push('/cards')" class="group cursor-pointer p-4 rounded-xl border border-border hover:border-violet-500/30 hover:bg-violet-500/5 transition-all duration-300 flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-full bg-violet-500/10 text-violet-600 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            <Icon :size="24"><CreditCard /></Icon>
          </div>
          <span class="text-sm font-medium text-card-foreground group-hover:text-violet-600">管理卡片</span>
        </div>

        <div @click="$router.push('/balance')" class="group cursor-pointer p-4 rounded-xl border border-border hover:border-emerald-500/30 hover:bg-emerald-500/5 transition-all duration-300 flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            <Icon :size="24"><Money /></Icon>
          </div>
          <span class="text-sm font-medium text-card-foreground group-hover:text-emerald-600">账户充值</span>
        </div>

        <div class="group cursor-not-allowed p-4 rounded-xl border border-border transition-all duration-300 flex flex-col items-center justify-center gap-3 opacity-60">
           <div class="w-12 h-12 rounded-full bg-muted text-muted-foreground/70 flex items-center justify-center shadow-inner">
             <Icon :size="24"><Plus /></Icon>
           </div>
          <span class="text-sm font-medium text-muted-foreground">更多功能</span>
        </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { balanceApi } from '@/api/balance'
import { zonesApi } from '@/api/zones'
import { cardsApi } from '@/api/cards'
import { useUserStore } from '@/stores/user'
import { 
  Wallet, Grid, CreditCard, Money, Top, Plus 
} from '@/icons'
import type { UserBalance, Zone } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const userStore = useUserStore()
const loading = ref(false)
const balance = ref<UserBalance | null>(null)
const zones = ref<Zone[]>([])
const cardCount = ref(0)

const fetchData = async () => {
  loading.value = true
  try {
    // 获取余额
    balance.value = await balanceApi.getMyBalance()

    // 获取专区
    const zonesResponse = await zonesApi.getZones()
    zones.value = zonesResponse.results

    // 获取虚拟卡数量
    const cardsResponse = await cardsApi.getMyCards()
    cardCount.value = cardsResponse.length
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>
