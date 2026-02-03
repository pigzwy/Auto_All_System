<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="px-4 py-3">
        <PageHeader @back="$router.push('/admin')" content="Google Business 插件仪表板" />
      </CardContent>
    </Card>

    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <Card class="relative overflow-hidden shadow-sm border-border/80 bg-background/80">
        <CardContent class="p-6 pb-16">
          <div class="flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Icon :size="30"><User /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-bold leading-none text-foreground">{{ accountStats.total || 0 }}</div>
              <div class="mt-1 text-sm text-muted-foreground">总账号数</div>
            </div>
          </div>
        </CardContent>
        <div class="absolute bottom-0 left-0 right-0 flex justify-between gap-2 bg-muted/30 px-6 py-3 text-xs text-muted-foreground">
          <span>待验证: {{ accountStats.pending || 0 }}</span>
          <span>已验证: {{ accountStats.verified || 0 }}</span>
          <span>已绑卡: {{ accountStats.subscribed || 0 }}</span>
        </div>
      </Card>

      <Card class="relative overflow-hidden shadow-sm border-border/80 bg-background/80">
        <CardContent class="p-6 pb-16">
          <div class="flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-500 text-white">
              <Icon :size="30"><DocumentChecked /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-bold leading-none text-foreground">{{ taskStats.total || 0 }}</div>
              <div class="mt-1 text-sm text-muted-foreground">总任务数</div>
            </div>
          </div>
        </CardContent>
        <div class="absolute bottom-0 left-0 right-0 flex justify-between gap-2 bg-muted/30 px-6 py-3 text-xs text-muted-foreground">
          <span>运行中: {{ taskStats.running || 0 }}</span>
          <span>已完成: {{ taskStats.completed || 0 }}</span>
          <span>失败: {{ taskStats.failed || 0 }}</span>
        </div>
      </Card>

      <Card class="relative overflow-hidden shadow-sm border-border/80 bg-background/80">
        <CardContent class="p-6 pb-16">
          <div class="flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-rose-500 text-white">
              <Icon :size="30"><CreditCard /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-bold leading-none text-foreground">{{ cardStats.total || 0 }}</div>
              <div class="mt-1 text-sm text-muted-foreground">总卡片数</div>
            </div>
          </div>
        </CardContent>
        <div class="absolute bottom-0 left-0 right-0 flex justify-between gap-2 bg-muted/30 px-6 py-3 text-xs text-muted-foreground">
          <span>可用: {{ cardStats.active || 0 }}</span>
          <span>已用: {{ cardStats.used || 0 }}</span>
          <span>使用次数: {{ cardStats.times_used || 0 }}</span>
        </div>
      </Card>

      <Card class="relative overflow-hidden shadow-sm border-border/80 bg-background/80">
        <CardContent class="p-6 pb-16">
          <div class="flex items-center gap-4">
            <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-amber-500 text-white">
              <Icon :size="30"><Coin /></Icon>
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-bold leading-none text-foreground">{{ costStats.total_cost || 0 }}</div>
              <div class="mt-1 text-sm text-muted-foreground">总费用（积分）</div>
            </div>
          </div>
        </CardContent>
        <div class="absolute bottom-0 left-0 right-0 flex justify-between gap-2 bg-muted/30 px-6 py-3 text-xs text-muted-foreground">
          <span>今日: {{ costStats.today_cost || 0 }}</span>
          <span>本周: {{ costStats.week_cost || 0 }}</span>
          <span>本月: {{ costStats.month_cost || 0 }}</span>
        </div>
      </Card>
    </div>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">快速操作</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Button  variant="default" type="button" class="w-full" @click="$router.push('/admin/google-business/accounts')">
            <Icon><UserFilled /></Icon>
            <span class="ml-1.5">管理账号</span>
          </Button>
          <Button variant="success" type="button" class="w-full" @click="$router.push('/admin/google-business/tasks/create')">
            <Icon><Plus /></Icon>
            <span class="ml-1.5">创建任务</span>
          </Button>
          <Button  variant="secondary" type="button" class="w-full" @click="$router.push('/admin/google-business/cards')">
            <Icon><CreditCard /></Icon>
            <span class="ml-1.5">管理卡片</span>
          </Button>
          <Button  variant="secondary" type="button" class="w-full" @click="$router.push('/admin/google-business/tasks')">
            <Icon><List /></Icon>
            <span class="ml-1.5">查看任务</span>
          </Button>
        </div>
      </CardContent>
    </Card>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Card class="shadow-sm border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between gap-4">
            <CardTitle class="text-base">任务趋势（最近7天）</CardTitle>
            <RadioGroup v-model="trendGroupBy" size="small" @change="loadTaskTrends">
              <RadioButton label="day">按天</RadioButton>
              <RadioButton label="week">按周</RadioButton>
              <RadioButton label="month">按月</RadioButton>
            </RadioGroup>
          </div>
        </CardHeader>
        <CardContent>
          <div ref="taskTrendChart" class="h-[300px]" />
        </CardContent>
      </Card>

      <Card class="shadow-sm border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between gap-4">
            <CardTitle class="text-base">费用统计（最近7天）</CardTitle>
            <RadioGroup v-model="costGroupBy" size="small" @change="loadCostStats">
              <RadioButton label="day">按天</RadioButton>
              <RadioButton label="week">按周</RadioButton>
              <RadioButton label="month">按月</RadioButton>
            </RadioGroup>
          </div>
        </CardHeader>
        <CardContent>
          <div ref="costStatsChart" class="h-[300px]" />
        </CardContent>
      </Card>
    </div>

      <Card class="shadow-sm border-border/80 bg-background/80">
      <CardHeader class="pb-3">
        <div class="flex items-center justify-between gap-4">
          <CardTitle class="text-base">最近任务</CardTitle>
          <Button text @click="$router.push('/admin/google-business/tasks')">
            查看全部
            <Icon><ArrowRight /></Icon>
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <DataTable :data="recentTasks" class="w-full">
            <DataColumn prop="id" label="ID" width="80" />
            <DataColumn prop="task_type" label="任务类型" width="120">
              <template #default="{ row }">
                <Tag :type="getTaskTypeColor(row.task_type)" size="small">
                  {{ getTaskTypeName(row.task_type) }}
                </Tag>
              </template>
            </DataColumn>
            <DataColumn prop="total_count" label="账号数" width="100" />
            <DataColumn prop="success_count" label="成功" width="80" />
            <DataColumn prop="failed_count" label="失败" width="80" />
            <DataColumn prop="status" label="状态" width="100">
              <template #default="{ row }">
                <Tag :type="getStatusColor(row.status)" size="small">
                  {{ getStatusName(row.status) }}
                </Tag>
              </template>
            </DataColumn>
            <DataColumn prop="total_cost" label="费用" width="100">
              <template #default="{ row }">
                <span class="font-semibold text-amber-600">{{ row.total_cost }}</span>
              </template>
            </DataColumn>
            <DataColumn prop="created_at" label="创建时间" width="180" />
            <DataColumn label="操作" width="150">
              <template #default="{ row }">
                <Button size="small" @click="viewTask(row.id)">查看</Button>
                <Button v-if="row.status === 'running'" size="small"  variant="destructive" type="button" @click="cancelTask(row.id)">
                  取消
                </Button>
              </template>
            </DataColumn>
          </DataTable>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { 
  User, 
  DocumentChecked, 
  CreditCard, 
  Plus
} from '@/icons'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useRouter } from 'vue-router'
// import * as echarts from 'echarts'
import {
  getAccountStats,
  getTaskStats,
  getCardStats,
  getDashboardStats,
  getTasks,
  getTaskTrends,
  getCostStats,
  cancelTask as cancelTaskApi
} from '@/api/google_business'

const router = useRouter()

// 统计数据
const accountStats = ref<any>({})
const taskStats = ref<any>({})
const cardStats = ref<any>({})
const costStats = ref<any>({})
const recentTasks = ref<any[]>([])

// 图表配置
const trendGroupBy = ref('day')
const costGroupBy = ref('day')
const taskTrendChart = ref<HTMLElement>()
const costStatsChart = ref<HTMLElement>()
let taskChart: any | null = null
let costChart: any | null = null

// 加载所有统计数据
const loadAllStats = async () => {
  try {
    // 并发加载所有统计数据
    const [accountRes, taskRes, cardRes, dashboardRes] = await Promise.all([
      getAccountStats(),
      getTaskStats(),
      getCardStats(),
      getDashboardStats()
    ])

    accountStats.value = accountRes.data || {}
    taskStats.value = taskRes.data || {}
    cardStats.value = cardRes.data || {}
    costStats.value = dashboardRes.data?.cost_stats || {}
  } catch (error: any) {
    console.error('加载统计数据失败:', error)
    ElMessage.error(error.response?.data?.error || '加载统计数据失败')
  }
}

// 加载最近任务
const loadRecentTasks = async () => {
  try {
    const res = await getTasks({ page: 1, page_size: 5, ordering: '-created_at' })
    recentTasks.value = res.data?.results || []
  } catch (error: any) {
    console.error('加载最近任务失败:', error)
  }
}

// 加载任务趋势
const loadTaskTrends = async () => {
  try {
    const res = await getTaskTrends({ group_by: trendGroupBy.value as 'day' | 'week' | 'month' })
    const data = res.data || []

    if (taskChart) {
      taskChart.setOption({
        tooltip: {
          trigger: 'axis'
        },
        legend: {
          data: ['成功', '失败', '总数']
        },
        xAxis: {
          type: 'category',
          data: data.map((item: any) => item.date)
        },
        yAxis: {
          type: 'value'
        },
        series: [
          {
            name: '成功',
            type: 'line',
            data: data.map((item: any) => item.success_count),
            smooth: true,
            itemStyle: { color: '#67C23A' }
          },
          {
            name: '失败',
            type: 'line',
            data: data.map((item: any) => item.failed_count),
            smooth: true,
            itemStyle: { color: '#F56C6C' }
          },
          {
            name: '总数',
            type: 'line',
            data: data.map((item: any) => item.total_count),
            smooth: true,
            itemStyle: { color: '#409EFF' }
          }
        ]
      })
    }
  } catch (error) {
    console.error('加载任务趋势失败:', error)
  }
}

// 加载费用统计
const loadCostStats = async () => {
  try {
    const res = await getCostStats({ group_by: costGroupBy.value as 'day' | 'week' | 'month' })
    const data = res.data || []

    if (costChart) {
      costChart.setOption({
        tooltip: {
          trigger: 'axis'
        },
        xAxis: {
          type: 'category',
          data: data.map((item: any) => item.date)
        },
        yAxis: {
          type: 'value',
          name: '费用（积分）'
        },
        series: [
          {
            type: 'bar',
            data: data.map((item: any) => item.cost),
            itemStyle: { color: '#E6A23C' }
          }
        ]
      })
    }
  } catch (error) {
    console.error('加载费用统计失败:', error)
  }
}

// 初始化图表
const initCharts = () => {
  // if (taskTrendChart.value) {
  //   taskChart = echarts.init(taskTrendChart.value)
  // }
  // if (costStatsChart.value) {
  //   costChart = echarts.init(costStatsChart.value)
  // }
  loadTaskTrends()
  loadCostStats()
}

// 查看任务详情
const viewTask = (taskId: number) => {
  router.push(`/admin/google-business/tasks/${taskId}`)
}

// 取消任务
const cancelTask = async (taskId: number) => {
  try {
    await cancelTaskApi(taskId)
    ElMessage.success('任务已取消')
    loadRecentTasks()
    loadAllStats()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '取消任务失败')
  }
}

// 获取任务类型名称
const getTaskTypeName = (type: string) => {
  const map: Record<string, string> = {
    login: '登录',
    get_link: '获取链接',
    verify: 'SheerID验证',
    bind_card: '绑卡订阅',
    one_click: '一键到底'
  }
  return map[type] || type
}

// 获取任务类型颜色
const getTaskTypeColor = (type: string) => {
  const map: Record<string, string> = {
    login: '',
    get_link: 'info',
    verify: 'warning',
    bind_card: 'success',
    one_click: 'danger'
  }
  return map[type] || ''
}

// 获取状态名称
const getStatusName = (status: string) => {
  const map: Record<string, string> = {
    pending: '待处理',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[status] || status
}

// 获取状态颜色
const getStatusColor = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: ''
  }
  return map[status] || ''
}

// 组件挂载
onMounted(async () => {
  await loadAllStats()
  await loadRecentTasks()
  initCharts()

  // 每30秒刷新一次数据
  const interval = setInterval(() => {
    loadAllStats()
    loadRecentTasks()
  }, 30000)

  // 组件卸载时清除定时器
  onUnmounted(() => {
    clearInterval(interval)
    if (taskChart) taskChart.dispose()
    if (costChart) costChart.dispose()
  })
})
</script>
