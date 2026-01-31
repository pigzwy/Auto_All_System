<template>
  <div class="space-y-6 p-5">
    <!-- 页头 -->
    <div>
      <div class="flex items-start justify-between gap-4">
        <h2 class="flex flex-wrap items-center gap-2 text-2xl font-bold tracking-tight text-foreground">
          <Icon class="align-middle"><Platform /></Icon>
          Google 业务自动化工作台
          <TooltipText placement="bottom" :show-after="200" effect="dark">
            <template #content>
              <div v-if="browserStatus" class="text-[13px] leading-relaxed">
                <div><strong>浏览器引擎:</strong> {{ browserStatus.default || '未知' }}</div>
                <div>
                  <strong>状态:</strong>
                  <span
                    class="font-semibold"
                    :class="browserStatus.engine_online ? 'text-emerald-300' : 'text-rose-300'"
                  >
                    {{ browserStatus.engine_online ? '在线 (Online)' : '离线 (Offline)' }}
                  </span>
                </div>
                <div v-if="browserStatus.pool">
                  <strong>连接池:</strong> {{ browserStatus.pool.busy }} / {{ browserStatus.pool.total }} (忙/总)
                </div>
                <div class="mt-2 border-t border-white/20 pt-1 text-xs text-white/70">
                  点击图标刷新状态
                </div>
              </div>
              <div v-else class="text-[13px]">正在获取状态...</div>
            </template>

            <Icon
              class="ml-1 cursor-pointer align-middle text-xl transition"
              :class="[
                isBrowserStatusLoading ? 'animate-spin cursor-wait text-sky-500' : '',
                !isBrowserStatusLoading && browserStatus?.engine_online ? 'text-emerald-600 hover:text-emerald-500 hover:scale-110' : '',
                !isBrowserStatusLoading && !browserStatus?.engine_online ? 'text-rose-600 hover:text-rose-500 hover:scale-110' : ''
              ]"
              @click="refreshBrowserStatus"
            >
              <Connection />
            </Icon>
          </TooltipText>
        </h2>
      </div>

      <p class="mt-1 text-sm text-muted-foreground">管理 Google 账号、SheerID 认证、自动绑卡订阅</p>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 md:grid-cols-4">
      <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-indigo-500 to-fuchsia-500 p-5 text-white shadow-sm">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-3xl font-bold leading-none">{{ statistics.total_accounts }}</div>
            <div class="mt-1 text-sm text-white/90">总账号数</div>
          </div>
          <Icon class="text-5xl opacity-30"><User /></Icon>
        </div>
      </div>

      <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-emerald-500 to-cyan-400 p-5 text-white shadow-sm">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-3xl font-bold leading-none">{{ statistics.status_breakdown.subscribed || 0 }}</div>
            <div class="mt-1 text-sm text-white/90">已订阅</div>
          </div>
          <Icon class="text-5xl opacity-30"><CircleCheck /></Icon>
        </div>
      </div>

      <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-sky-500 to-cyan-400 p-5 text-white shadow-sm">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-3xl font-bold leading-none">{{ statistics.today_tasks }}</div>
            <div class="mt-1 text-sm text-white/90">今日任务</div>
          </div>
          <Icon class="text-5xl opacity-30"><Clock /></Icon>
        </div>
      </div>

      <div class="relative overflow-hidden rounded-xl bg-gradient-to-br from-rose-500 to-amber-400 p-5 text-white shadow-sm">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-3xl font-bold leading-none">{{ statistics.success_rate }}%</div>
            <div class="mt-1 text-sm text-white/90">成功率</div>
          </div>
          <Icon class="text-5xl opacity-30"><TrendCharts /></Icon>
        </div>
      </div>
    </div>

    <!-- 状态分布和最近活动 -->
    <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
      <Card class="shadow-sm">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">账号状态分布</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable :data="statusList" class="w-full">
            <DataColumn label="状态" width="200">
              <template #default="{ row }">
                <Tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </Tag>
              </template>
            </DataColumn>
            <DataColumn label="数量" align="right">
              <template #default="{ row }">
                <span class="text-base font-semibold text-primary">{{ row.count }}</span>
              </template>
            </DataColumn>
          </DataTable>
        </CardContent>
      </Card>

      <Card class="shadow-sm">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">最近活动</CardTitle>
        </CardHeader>
        <CardContent>
          <Timeline v-if="statistics.recent_activities && statistics.recent_activities.length > 0">
            <TimelineItem
              v-for="(activity, index) in statistics.recent_activities"
              :key="index"
              :timestamp="formatTime(activity.created_at)"
              placement="top"
              :color="getTaskStatusColor(activity.status)"
            >
              <div class="space-y-1">
                <div class="text-sm font-semibold text-foreground">{{ activity.task_type }}</div>
                <div class="text-xs text-muted-foreground">{{ activity.account_email }}</div>
                <Tag :type="getTaskStatusType(activity.status)" size="small">
                  {{ activity.status }}
                </Tag>
              </div>
            </TimelineItem>
          </Timeline>
          <div v-else class="rounded-lg border border-border bg-muted/10 p-8 text-center">
            <div class="text-sm font-medium text-foreground">暂无活动记录</div>
            <div class="mt-1 text-xs text-muted-foreground">稍后刷新再试</div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 快速操作 -->
    <Card class="shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">快速操作</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
          <Button  variant="default" type="button" size="large" class="w-full" @click="$router.push('/google/accounts')">
            <Icon><UserFilled /></Icon>
            <span class="ml-2">管理账号</span>
          </Button>

          <Button  variant="default" type="button" size="large" class="w-full" @click="$router.push('/google/sheerid')">
            <Icon><Check /></Icon>
            <span class="ml-2">SheerID 认证</span>
          </Button>

          <Button  variant="secondary" type="button" size="large" class="w-full" @click="$router.push('/google/bind-card')">
            <Icon><CreditCard /></Icon>
            <span class="ml-2">自动绑卡</span>
          </Button>

          <Button  variant="secondary" type="button" size="large" class="w-full" @click="$router.push('/google/auto-all')">
            <Icon><MagicStick /></Icon>
            <span class="ml-2">一键全自动</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Platform,
  User,
  CircleCheck,
  Clock,
  TrendCharts,
  UserFilled,
  Check,
  CreditCard,
  MagicStick,
  Connection
} from '@/icons'
import { getGoogleStatistics } from '@/api/google_business'
import { googleBrowserApi } from '@/api/google'

// const router = useRouter()

interface Statistics {
  total_accounts: number
  status_breakdown: Record<string, number>
  today_tasks: number
  success_rate: number
  recent_activities: Array<{
    task_type: string
    account_email: string
    status: string
    created_at: string
  }>
}

const statistics = ref<Statistics>({
  total_accounts: 0,
  status_breakdown: {},
  today_tasks: 0,
  success_rate: 0,
    recent_activities: []
})

const browserStatus = ref<any>(null)
const isBrowserStatusLoading = ref(false)

const fetchBrowserStatus = async () => {
  isBrowserStatusLoading.value = true
  try {
    const res = await googleBrowserApi.getStatus()
    // request.ts interceptor returns raw data, not AxiosResponse
    browserStatus.value = res
  } catch (error) {
    console.error('获取浏览器状态失败', error)
    browserStatus.value = { engine_online: false, default: 'unknown' }
  } finally {
    isBrowserStatusLoading.value = false
  }
}

const refreshBrowserStatus = async () => {
  await fetchBrowserStatus()
  if (browserStatus.value?.engine_online) {
    ElMessage.success('浏览器引擎连接正常')
  } else {
    ElMessage.warning('浏览器引擎未连接')
  }
}

const statusList = computed(() => {
  return Object.entries(statistics.value.status_breakdown).map(([status, count]) => ({
    status,
    count
  }))
})

const loadStatistics = async () => {
  try {
    const raw = await getGoogleStatistics()
    // Adapt backend statistics/overview payload to the UI shape
    const status_breakdown = {
      pending_check: raw?.pending ?? 0,
      link_ready: raw?.link_ready ?? 0,
      verified: raw?.verified ?? 0,
      subscribed: raw?.subscribed ?? 0,
      ineligible: raw?.ineligible ?? 0,
      error: raw?.error ?? 0,
    }
    statistics.value = {
      total_accounts: raw?.total ?? 0,
      status_breakdown,
      today_tasks: 0,
      success_rate: 0,
      recent_activities: [],
    }
  } catch (error: any) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    'pending_check': 'info',
    'link_ready': 'primary',
    'verified': 'warning',
    'subscribed': 'success',
    'ineligible': 'danger',
    'error': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'pending_check': '待检测资格',
    'link_ready': '有资格待验证',
    'verified': '已验证未绑卡',
    'subscribed': '已订阅',
    'ineligible': '无资格',
    'error': '错误'
  }
  return texts[status] || status
}

const getTaskStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    '等待中': '#909399',
    '运行中': '#409EFF',
    '成功': '#67C23A',
    '失败': '#F56C6C',
    '已取消': '#E6A23C'
  }
  return colors[status] || '#909399'
}

const getTaskStatusType = (status: string) => {
  const types: Record<string, any> = {
    '等待中': 'info',
    '运行中': 'primary',
    '成功': 'success',
    '失败': 'danger',
    '已取消': 'warning'
  }
  return types[status] || 'info'
}

const formatTime = (datetime: string) => {
  if (!datetime) return ''
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadStatistics()
  fetchBrowserStatus()
  // 每30秒刷新一次统计数据
  setInterval(loadStatistics, 30000)
})
</script>
