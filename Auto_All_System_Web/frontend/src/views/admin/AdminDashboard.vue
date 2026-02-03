<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">管理后台</h1>
        <p class="mt-1 text-sm text-muted-foreground">系统概览与快捷入口</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6">
          <div class="flex items-center gap-4">
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-emerald-500 text-white shadow-sm">
              <Icon :size="22"><User /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">{{ stats.totalUsers || 0 }}</div>
              <div class="mt-1 text-xs text-muted-foreground">总用户数</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6">
          <div class="flex items-center gap-4">
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 text-white shadow-sm">
              <Icon :size="22"><List /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">{{ stats.totalTasks || 0 }}</div>
              <div class="mt-1 text-xs text-muted-foreground">总任务数</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6">
          <div class="flex items-center gap-4">
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 text-white shadow-sm">
              <Icon :size="22"><Money /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">¥{{ stats.totalRevenue || 0 }}</div>
              <div class="mt-1 text-xs text-muted-foreground">总收入</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6">
          <div class="flex items-center gap-4">
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-sky-500 text-white shadow-sm">
              <Icon :size="22"><CreditCard /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">{{ stats.totalCards || 0 }}</div>
              <div class="mt-1 text-xs text-muted-foreground">虚拟卡总数</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 图表区域 -->
    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle class="text-base">用户增长趋势</CardTitle>
            <CardDescription class="text-xs">占位</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
            <div class="h-[300px]">
              <div class="flex h-full items-center justify-center rounded-xl border border-border bg-gradient-to-br from-muted/40 via-background to-muted/10 text-sm text-muted-foreground">
                用户增长图表
              </div>
            </div>
        </CardContent>
      </Card>

      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardHeader>
          <div class="flex items-center justify-between">
            <CardTitle class="text-base">任务完成率</CardTitle>
            <CardDescription class="text-xs">占位</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
            <div class="h-[300px]">
              <div class="flex h-full items-center justify-center rounded-xl border border-border bg-gradient-to-br from-muted/40 via-background to-muted/10 text-sm text-muted-foreground">
                任务完成率图表
              </div>
            </div>
        </CardContent>
      </Card>
    </div>

    <!-- 快速操作 -->
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardHeader>
        <div class="flex items-center justify-between">
          <CardTitle class="text-base">快速操作</CardTitle>
          <CardDescription class="text-xs">常用入口</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          <button
            v-for="action in quickActions"
            :key="action.name"
            type="button"
            class="group w-full rounded-2xl border border-border bg-background/70 p-4 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:bg-primary/5 hover:shadow-md"
            @click="handleAction(action.route)"
          >
            <div class="flex items-center gap-3">
              <div class="flex h-11 w-11 items-center justify-center rounded-xl bg-muted">
                <Icon :size="24" :color="action.color">
                  <component :is="action.icon" />
                </Icon>
              </div>
              <div class="min-w-0">
                <div class="truncate text-sm font-medium text-foreground">{{ action.name }}</div>
                <div class="mt-1 truncate text-xs text-muted-foreground">点击进入</div>
              </div>
            </div>
          </button>
        </div>
      </CardContent>
    </Card>

    <!-- 最近活动 -->
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardHeader>
        <div class="flex items-center justify-between">
          <CardTitle class="text-base">最近活动</CardTitle>
          <CardDescription class="text-xs">系统事件</CardDescription>
        </div>
      </CardHeader>
      <CardContent>
        <div class="relative pl-5">
          <div class="absolute left-2 top-0 h-full w-px bg-border" />
          <div
            v-for="(activity, idx) in recentActivities"
            :key="activity.id"
            class="relative pb-4"
            :class="idx === recentActivities.length - 1 ? 'pb-0' : ''"
          >
            <div class="absolute -left-[1px] top-1.5 h-2.5 w-2.5 rounded-full bg-primary/60" />
            <div class="flex items-start justify-between gap-4">
              <span class="text-sm text-foreground">{{ activity.content }}</span>
              <span class="shrink-0 text-xs text-muted-foreground">{{ activity.time }}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { User, List, Money, CreditCard, Setting, DataAnalysis, UserFilled, Tickets } from '@/icons'
import adminApi, { type DashboardStats } from '@/api/admin'
import { ElMessage } from '@/lib/element'

const router = useRouter()

const stats = ref({
  totalUsers: 0,
  totalTasks: 0,
  totalRevenue: 0,
  totalCards: 0
})

const quickActions = [
  { name: '用户管理', icon: UserFilled, route: '/admin/users', color: '#409EFF' },
  { name: '任务管理', icon: List, route: '/admin/tasks', color: '#67C23A' },
  { name: '虚拟卡管理', icon: Tickets, route: '/admin/cards', color: '#E6A23C' },
  { name: '系统设置', icon: Setting, route: '/admin/settings', color: '#F56C6C' },
  { name: '数据分析', icon: DataAnalysis, route: '/admin/analytics', color: '#909399' },
  { name: '专区管理', icon: Setting, route: '/admin/zones', color: '#409EFF' },
]

const recentActivities = ref([
  { id: 1, time: '2分钟前', type: 'success', content: '用户 testuser 注册成功' },
  { id: 2, time: '5分钟前', type: 'primary', content: '任务 #123 执行完成' },
  { id: 3, time: '10分钟前', type: 'warning', content: '虚拟卡 ****1234 使用次数达到上限' },
  { id: 4, time: '15分钟前', type: 'info', content: '系统自动备份已完成' },
])

const handleAction = (route: string) => {
  router.push(route)
}

const fetchStats = async () => {
  try {
    const data: DashboardStats = await adminApi.getDashboardStats()
    stats.value = {
      totalUsers: data.users.total,
      totalTasks: data.tasks.total,
      totalRevenue: data.revenue.total,
      totalCards: data.cards.total
    }
  } catch (error) {
    console.error('Failed to fetch stats:', error)
    ElMessage.error('获取统计数据失败')
  }
}

onMounted(() => {
  fetchStats()
})
</script>
