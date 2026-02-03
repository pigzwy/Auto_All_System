<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="px-4 py-3">
        <PageHeader @back="$router.push('/admin/google-business/tasks')" :content="`任务详情 #${taskId}`" />
      </CardContent>
    </Card>

    <div class="space-y-6">
      <div v-loading="loading">
        <Card class="shadow-sm border-border/80 bg-background/80">
          <CardHeader class="pb-3">
            <div class="flex items-center justify-between gap-4">
              <CardTitle class="text-base">任务信息</CardTitle>
              <div class="flex items-center gap-2">
                <Button
                  v-if="task.status === 'running'"
                   variant="secondary" type="button"
                  @click="cancelTask"
                >
                  取消任务
                </Button>
                <Button  variant="default" type="button" @click="loadTask">
                  <Icon><Refresh /></Icon>
                  刷新
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent class="space-y-5">
            <Descriptions :column="3" border>
            <DescriptionsItem label="任务ID">
              {{ task.id }}
            </DescriptionsItem>
            <DescriptionsItem label="任务类型">
              <Tag :type="getTaskTypeColor(task.task_type)" size="small">
                {{ getTaskTypeName(task.task_type) }}
              </Tag>
            </DescriptionsItem>
            <DescriptionsItem label="状态">
              <Tag :type="getStatusColor(task.status)" size="small">
                {{ getStatusName(task.status) }}
              </Tag>
            </DescriptionsItem>

            <DescriptionsItem label="总账号数">
              {{ task.total_count }}
            </DescriptionsItem>
            <DescriptionsItem label="成功数">
              <span class="font-semibold text-emerald-600">{{ task.success_count }}</span>
            </DescriptionsItem>
            <DescriptionsItem label="失败数">
              <span class="font-semibold text-rose-600">{{ task.failed_count }}</span>
            </DescriptionsItem>

            <DescriptionsItem label="总费用">
              <span class="font-semibold text-amber-600">{{ task.total_cost }} 积分</span>
            </DescriptionsItem>
            <DescriptionsItem label="创建时间">
              {{ task.created_at }}
            </DescriptionsItem>
            <DescriptionsItem label="开始时间">
              {{ task.started_at || '-' }}
            </DescriptionsItem>

            <DescriptionsItem label="完成时间">
              {{ task.completed_at || '-' }}
            </DescriptionsItem>
            <DescriptionsItem label="耗时">
              {{ getDuration(task) }}
            </DescriptionsItem>
            <DescriptionsItem label="错误信息">
              {{ task.error_message || '-' }}
            </DescriptionsItem>
          </Descriptions>

          <!-- 进度条 -->
          <div class="mt-5">
            <ProgressBar
              :percentage="getProgress(task)"
              :status="task.status === 'completed' ? 'success' : task.status === 'failed' ? 'exception' : undefined"
            >
              <template #default="{ percentage }">
                <span>{{ percentage }}% ({{ task.success_count + task.failed_count }} / {{ task.total_count }})</span>
              </template>
            </ProgressBar>
          </div>
          </CardContent>
        </Card>
      </div>

      <!-- 任务账号列表 -->
      <Card class="shadow-sm border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle class="text-base">任务账号列表</CardTitle>
            <RadioGroup v-model="accountStatusFilter" size="small" @change="loadTaskAccounts">
              <RadioButton label="">全部</RadioButton>
              <RadioButton label="pending">待处理</RadioButton>
              <RadioButton label="running">运行中</RadioButton>
              <RadioButton label="completed">已完成</RadioButton>
              <RadioButton label="failed">失败</RadioButton>
            </RadioGroup>
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            v-loading="accountsLoading"
            :data="taskAccounts"
            class="w-full"
          >
            <DataColumn prop="id" label="ID" width="80" />
            
            <DataColumn prop="google_account.email" label="账号邮箱" min-width="200">
              <template #default="{ row }">
                {{ row.google_account?.email || '-' }}
              </template>
            </DataColumn>

            <DataColumn prop="status" label="状态" width="120">
              <template #default="{ row }">
                <Tag :type="getAccountStatusColor(row.status)" size="small">
                  {{ getAccountStatusName(row.status) }}
                </Tag>
              </template>
            </DataColumn>

            <DataColumn prop="result_message" label="结果" min-width="200" />

            <DataColumn prop="cost" label="费用" width="100">
              <template #default="{ row }">
                <span class="text-amber-600">{{ row.cost }}</span>
              </template>
            </DataColumn>

            <DataColumn prop="started_at" label="开始时间" width="180" />
            
            <DataColumn prop="completed_at" label="完成时间" width="180" />

            <DataColumn label="操作" width="150">
              <template #default="{ row }">
                <Button size="small" @click="viewAccountDetail(row)">
                  查看详情
                </Button>
                <Button
                  v-if="row.status === 'failed'"
                  size="small"
                   variant="default" type="button"
                  @click="retryAccount(row.id)"
                >
                  重试
                </Button>
              </template>
            </DataColumn>
          </DataTable>

          <!-- 分页 -->
          <div class="mt-5 flex justify-end">
            <Paginator
              v-model:current-page="accountPagination.page"
              v-model:page-size="accountPagination.page_size"
              :page-sizes="[10, 20, 50]"
              :total="accountPagination.total"
              layout="total, sizes, prev, pager, next"
              @size-change="loadTaskAccounts"
              @current-change="loadTaskAccounts"
            />
          </div>
        </CardContent>
      </Card>

      <!-- 任务日志 -->
      <Card class="shadow-sm border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between gap-4">
            <CardTitle class="text-base">任务日志</CardTitle>
            <Button size="small" @click="loadTaskLogs">
              <Icon><Refresh /></Icon>
              刷新
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          <DataTable
            v-loading="logsLoading"
            :data="taskLogs"
            class="w-full"
            max-height="400"
          >
            <DataColumn prop="created_at" label="时间" width="180" />
            
            <DataColumn prop="level" label="级别" width="100">
              <template #default="{ row }">
                <Tag :type="getLogLevelColor(row.level)" size="small">
                  {{ row.level }}
                </Tag>
              </template>
            </DataColumn>

            <DataColumn prop="message" label="消息" min-width="400" />

            <DataColumn prop="account_email" label="账号" width="200" />
          </DataTable>

          <!-- 分页 -->
          <div class="mt-5 flex justify-end">
            <Paginator
              v-model:current-page="logPagination.page"
              v-model:page-size="logPagination.page_size"
              :page-sizes="[20, 50, 100]"
              :total="logPagination.total"
              layout="total, sizes, prev, pager, next"
              @size-change="loadTaskLogs"
              @current-change="loadTaskLogs"
            />
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 账号详情对话框 -->
    <Modal
      v-model="accountDetailVisible"
      title="账号详情"
      width="600px"
    >
      <Descriptions :column="1" border>
        <DescriptionsItem label="账号邮箱">
          {{ selectedAccount?.google_account?.email }}
        </DescriptionsItem>
        <DescriptionsItem label="浏览器ID">
          {{ selectedAccount?.browser_id || '-' }}
        </DescriptionsItem>
        <DescriptionsItem label="状态">
          <Tag :type="getAccountStatusColor(selectedAccount?.status)" size="small">
            {{ getAccountStatusName(selectedAccount?.status) }}
          </Tag>
        </DescriptionsItem>
        <DescriptionsItem label="结果消息">
          {{ selectedAccount?.result_message || '-' }}
        </DescriptionsItem>
        <DescriptionsItem label="错误消息">
          {{ selectedAccount?.error_message || '-' }}
        </DescriptionsItem>
        <DescriptionsItem label="费用">
          {{ selectedAccount?.cost }} 积分
        </DescriptionsItem>
        <DescriptionsItem label="开始时间">
          {{ selectedAccount?.started_at || '-' }}
        </DescriptionsItem>
        <DescriptionsItem label="完成时间">
          {{ selectedAccount?.completed_at || '-' }}
        </DescriptionsItem>
        <DescriptionsItem label="结果数据">
          <pre class="mt-2 max-h-[200px] overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted/30 p-3 text-xs text-foreground">{{ JSON.stringify(selectedAccount?.result_data, null, 2) }}</pre>
        </DescriptionsItem>
      </Descriptions>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { useRoute } from 'vue-router'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  getTask,
  getTaskAccounts,
  getTaskLogs,
  cancelTask as cancelTaskApi,
  retryTaskAccounts
} from '@/api/google_business'

const route = useRoute()
// const router = useRouter()

const taskId = Number(route.params.id)

// 数据
const task = ref<any>({})
const taskAccounts = ref<any[]>([])
const taskLogs = ref<any[]>([])
const loading = ref(false)
const accountsLoading = ref(false)
const logsLoading = ref(false)

// 筛选和分页
const accountStatusFilter = ref('')
const accountPagination = ref({
  page: 1,
  page_size: 20,
  total: 0
})
const logPagination = ref({
  page: 1,
  page_size: 20,
  total: 0
})

// 账号详情对话框
const accountDetailVisible = ref(false)
const selectedAccount = ref<any>(null)

// 加载任务信息
const loadTask = async () => {
  loading.value = true
  try {
    const res = await getTask(taskId)
    task.value = res.data || {}
  } catch (error: any) {
    console.error('加载任务信息失败:', error)
    ElMessage.error(error.response?.data?.error || '加载任务信息失败')
  } finally {
    loading.value = false
  }
}

// 加载任务账号
const loadTaskAccounts = async () => {
  accountsLoading.value = true
  try {
    const res = await getTaskAccounts({
      task_id: taskId,
      status: accountStatusFilter.value || undefined,
      page: accountPagination.value.page,
      page_size: accountPagination.value.page_size
    })

    taskAccounts.value = res.data?.results || []
    accountPagination.value.total = res.data?.count || 0
  } catch (error: any) {
    console.error('加载任务账号失败:', error)
  } finally {
    accountsLoading.value = false
  }
}

// 加载任务日志
const loadTaskLogs = async () => {
  logsLoading.value = true
  try {
    const res = await getTaskLogs(taskId, {
      page: logPagination.value.page,
      page_size: logPagination.value.page_size
    })

    taskLogs.value = res.data?.results || []
    logPagination.value.total = res.data?.count || 0
  } catch (error: any) {
    console.error('加载任务日志失败:', error)
  } finally {
    logsLoading.value = false
  }
}

// 取消任务
const cancelTask = async () => {
  try {
    await ElMessageBox.confirm('确定要取消此任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await cancelTaskApi(taskId)
    ElMessage.success('任务已取消')
    loadTask()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '取消任务失败')
    }
  }
}

// 重试账号
const retryAccount = async (accountId: number) => {
  try {
    await retryTaskAccounts(taskId, { account_ids: [accountId] })
    ElMessage.success('重试任务已创建')
    loadTaskAccounts()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '重试失败')
  }
}

// 查看账号详情
const viewAccountDetail = (account: any) => {
  selectedAccount.value = account
  accountDetailVisible.value = true
}

// 计算进度
const getProgress = (task: any) => {
  if (task.total_count === 0) return 0
  return Math.round(((task.success_count + task.failed_count) / task.total_count) * 100)
}

// 计算耗时
const getDuration = (task: any) => {
  if (!task.started_at) return '-'
  
  const end = task.completed_at ? new Date(task.completed_at) : new Date()
  const start = new Date(task.started_at)
  const diffMs = end.getTime() - start.getTime()
  
  const minutes = Math.floor(diffMs / 60000)
  const seconds = Math.floor((diffMs % 60000) / 1000)
  
  return `${minutes}分${seconds}秒`
}

// 辅助函数
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

const getAccountStatusName = (status: string) => {
  const map: Record<string, string> = {
    pending: '待处理',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    skipped: '已跳过'
  }
  return map[status] || status
}

const getAccountStatusColor = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    skipped: ''
  }
  return map[status] || ''
}

const getLogLevelColor = (level: string) => {
  const map: Record<string, string> = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'danger',
    DEBUG: ''
  }
  return map[level] || ''
}

// 组件挂载
onMounted(async () => {
  await Promise.all([loadTask(), loadTaskAccounts(), loadTaskLogs()])

  // 每10秒刷新一次（如果任务还在运行）
  const interval = setInterval(() => {
    if (task.value.status === 'running') {
      loadTask()
      loadTaskAccounts()
    }
  }, 10000)

  onUnmounted(() => {
    clearInterval(interval)
  })
})
</script>
