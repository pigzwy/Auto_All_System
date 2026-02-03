<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardHeader>
        <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div class="flex items-center gap-2">
            <Icon color="#0EA5E9"><MagicStick /></Icon>
            <CardTitle class="text-base">一键全自动处理</CardTitle>
          </div>
          <Tag type="info" size="large">
            登录 → 检测 → 验证 → 绑卡 → 订阅
          </Tag>
        </div>
      </CardHeader>

      <CardContent class="space-y-6">
        <InfoAlert type="info" :closable="false">
          <template #title>
            <strong>自动执行完整流程：</strong>Google登录、状态检测、SheerID验证、绑卡订阅
          </template>
        </InfoAlert>

        <!-- 配置区域 -->
        <SimpleForm :model="config" label-width="150px">
          <div class="grid grid-cols-1 gap-4 md:grid-cols-12">
            <div class="md:col-span-6">
              <SimpleFormItem label="SheerID API Key" required>
                <TextInput
                  v-model="config.apiKey"
                  type="password"
                  show-password
                  placeholder="必填：用于SheerID验证"
                >
                  <template #prefix>
                    <Icon><Key /></Icon>
                  </template>
                </TextInput>
              </SimpleFormItem>
            </div>
            <div class="md:col-span-3">
              <SimpleFormItem label="一卡几绑">
                <NumberInput
                  v-model="config.cardsPerAccount"
                  :min="1"
                  :max="100"
                  controls-position="right"
                  class="w-full"
                />
              </SimpleFormItem>
            </div>
            <div class="md:col-span-3">
              <SimpleFormItem label="并发数">
                <NumberInput
                  v-model="config.threadCount"
                  :min="1"
                  :max="20"
                  controls-position="right"
                  class="w-full"
                />
              </SimpleFormItem>
            </div>
          </div>

          <!-- 延迟设置 -->
          <Collapse v-model="activeCollapse" class="mt-5">
            <CollapseItem title="高级延迟设置（秒）" name="delays">
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
                <SimpleFormItem label="点击 Get Offer 后">
                  <NumberInput v-model="config.delays.afterOffer" :min="1" :max="60" class="w-full" />
                </SimpleFormItem>
                <SimpleFormItem label="点击 Add Card 后">
                  <NumberInput v-model="config.delays.afterAddCard" :min="1" :max="60" class="w-full" />
                </SimpleFormItem>
                <SimpleFormItem label="点击 Save 后">
                  <NumberInput v-model="config.delays.afterSave" :min="1" :max="60" class="w-full" />
                </SimpleFormItem>
                <SimpleFormItem label="订阅完成后">
                  <NumberInput v-model="config.delays.afterSubscribe" :min="1" :max="60" class="w-full" />
                </SimpleFormItem>
              </div>
            </CollapseItem>

            <CollapseItem title="高级选项" name="advanced">
              <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
                <SimpleFormItem label="跳过状态检测">
                  <Toggle v-model="config.skipStatusCheck" />
                  <div class="mt-1 text-xs text-muted-foreground">直接进行验证和绑卡</div>
                </SimpleFormItem>
                <SimpleFormItem label="失败后重试">
                  <Toggle v-model="config.retryOnFailure" />
                  <div class="mt-1 text-xs text-muted-foreground">任务失败后自动重试</div>
                </SimpleFormItem>
              </div>
            </CollapseItem>
          </Collapse>
        </SimpleForm>

        <!-- 统计信息 -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-8">
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="总账号" :value="stats.totalAccounts" />
          </div>
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="可用卡片" :value="stats.availableCards" />
          </div>
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="待处理" :value="stats.pending" />
          </div>
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="处理中" :value="stats.processing" />
          </div>
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="已完成" :value="stats.completed" />
          </div>
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="失败" :value="stats.failed" />
          </div>
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="已订阅" :value="stats.subscribed" />
          </div>
          <div class="rounded-xl border border-border bg-background/70 p-4 shadow-sm">
            <Statistic title="成功率" :value="successRate" suffix="%" />
          </div>
        </div>

        <!-- 账号列表 -->
        <DataTable
          :data="accounts"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          stripe
          max-height="400"
          class="w-full"
        >
          <DataColumn type="selection" width="55" />
          <DataColumn prop="email" label="邮箱" min-width="200" />
          <DataColumn prop="status" label="状态" width="120">
            <template #default="{ row }">
              <Tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </Tag>
            </template>
          </DataColumn>
          <DataColumn prop="current_step" label="当前步骤" width="150">
            <template #default="{ row }">
              <span v-if="row.current_step">{{ row.current_step }}</span>
              <span v-else class="text-muted-foreground">-</span>
            </template>
          </DataColumn>
          <DataColumn prop="progress" label="进度" width="150">
            <template #default="{ row }">
              <ProgressBar
                v-if="row.progress !== undefined"
                :percentage="row.progress"
                :status="getProgressStatus(row.status)"
              />
            </template>
          </DataColumn>
          <DataColumn prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.updated_at) }}
            </template>
          </DataColumn>
        </DataTable>

        <!-- 操作按钮 -->
        <div class="flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
          <Button
             variant="default" type="button"
            size="large"
            class="w-full sm:w-auto"
            :disabled="!config.apiKey || !selectedAccounts.length || processing"
            :loading="processing"
            @click="startAutoAll"
          >
            <Icon><VideoPlay /></Icon>
            <span class="ml-1.5">开始执行选中账号</span>
          </Button>
          <Button
             variant="secondary" type="button"
            size="large"
            class="w-full sm:w-auto"
            :disabled="!processing"
            @click="stopAutoAll"
          >
            <Icon><VideoPause /></Icon>
            <span class="ml-1.5">暂停任务</span>
          </Button>
          <Button
             variant="destructive" type="button"
            size="large"
            class="w-full sm:w-auto"
            @click="resetAll"
          >
            <Icon><RefreshLeft /></Icon>
            <span class="ml-1.5">重置所有</span>
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- 实时日志对话框 -->
    <Modal
      v-model="logDialog"
      title="实时日志"
      width="900px"
      :close-on-click-modal="false"
    >
      <Scrollbar height="500px">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="flex items-start gap-2 border-b border-border p-2.5"
          :class="
            log.type === 'success'
              ? 'bg-emerald-500/10'
              : log.type === 'error'
                ? 'bg-rose-500/10'
                : log.type === 'warning'
                  ? 'bg-amber-500/10'
                  : ''
          "
        >
          <Tag :type="getLogType(log.type)" size="small">
            {{ log.timestamp }}
          </Tag>
          <span class="break-words text-sm text-foreground">{{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" class="p-8 text-center">
          <div class="text-sm font-medium text-foreground">暂无日志</div>
          <div class="mt-1 text-xs text-muted-foreground">开始任务后会在这里显示实时输出</div>
        </div>
      </Scrollbar>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  MagicStick,
  Key,
  VideoPlay,
  VideoPause,
  RefreshLeft
} from '@/icons'
import { getGoogleAccounts, createGoogleTask, getCards } from '@/api/google_business'

interface Account {
  id: number
  email: string
  status: string
  current_step?: string
  progress?: number
  updated_at: string
}

interface Card {
  id: number
  masked_number: string
  exp_month: string
  exp_year: string
  usage_count: number
  max_usage: number
  is_active: boolean
  is_available: boolean
}

const accounts = ref<Account[]>([])
const cards = ref<Card[]>([])
const selectedAccounts = ref<Account[]>([])
const loading = ref(false)
const processing = ref(false)
const logDialog = ref(false)
const activeCollapse = ref<string[]>([])

const config = reactive({
  apiKey: '',
  cardsPerAccount: 5,
  threadCount: 3,
  skipStatusCheck: false,
  retryOnFailure: true,
  delays: {
    afterOffer: 5,
    afterAddCard: 3,
    afterSave: 5,
    afterSubscribe: 3
  }
})

const stats = reactive({
  totalAccounts: 0,
  availableCards: 0,
  pending: 0,
  processing: 0,
  completed: 0,
  failed: 0,
  subscribed: 0
})

const logs = ref<any[]>([])

const successRate = computed(() => {
  if (stats.totalAccounts === 0) return 0
  return Math.round((stats.subscribed / stats.totalAccounts) * 100)
})

const loadAccounts = async () => {
  loading.value = true
  try {
    const response = await getGoogleAccounts({})
    accounts.value = (response as any) || []
    updateStats()
  } catch (error: any) {
    console.error('加载账号失败:', error)
    ElMessage.error('加载账号失败')
  } finally {
    loading.value = false
  }
}

const loadCards = async () => {
  try {
    const response = await getCards({ is_active: true })
    // 过滤出可用的卡片
    const allCards = (response.data as any) || []
    cards.value = allCards.filter((c: Card) => c.is_available)
    updateStats()
  } catch (error: any) {
    console.error('加载卡片失败:', error)
    ElMessage.error('加载卡片失败')
  }
}

const updateStats = () => {
  stats.totalAccounts = accounts.value.length
  stats.availableCards = cards.value.filter(c => c.is_available).length
  stats.pending = accounts.value.filter(a => a.status === 'pending_check').length
  stats.processing = accounts.value.filter(a => a.status === 'processing').length
  stats.completed = accounts.value.filter(a => ['verified', 'subscribed'].includes(a.status)).length
  stats.failed = accounts.value.filter(a => a.status === 'error').length
  stats.subscribed = accounts.value.filter(a => a.status === 'subscribed').length
}

const handleSelectionChange = (selection: Account[]) => {
  selectedAccounts.value = selection
}

const startAutoAll = async () => {
  if (!config.apiKey) {
    ElMessage.warning('请输入 SheerID API Key')
    return
  }

  if (!selectedAccounts.value.length) {
    ElMessage.warning('请选择要处理的账号')
    return
  }

  processing.value = true
  logDialog.value = true
  logs.value = []

  try {
    const accountIds = selectedAccounts.value.map(a => a.id)
    await createGoogleTask({
      task_type: 'auto_all',
      account_ids: accountIds,
      config: {
        api_key: config.apiKey,
        cards_per_account: config.cardsPerAccount,
        thread_count: config.threadCount,
        skip_status_check: config.skipStatusCheck,
        retry_on_failure: config.retryOnFailure,
        delays: config.delays
      }
    })

    ElMessage.success('自动化任务已启动')
    addLog('任务已提交，开始执行...', 'success')
  } catch (error: any) {
    ElMessage.error('任务启动失败')
    addLog(`错误: ${error.message}`, 'error')
  } finally {
    processing.value = false
  }
}

const stopAutoAll = () => {
  ElMessage.info('暂停功能开发中')
}

const resetAll = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要重置所有账号状态吗？',
      '确认重置',
      {
        confirmButtonText: '重置',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    ElMessage.info('重置功能开发中')
  } catch {
    // 用户取消
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    'pending_check': 'info',
    'processing': 'primary',
    'verified': 'warning',
    'subscribed': 'success',
    'error': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'pending_check': '待检测',
    'processing': '处理中',
    'verified': '已验证',
    'subscribed': '已订阅',
    'error': '错误'
  }
  return texts[status] || status
}

const getProgressStatus = (status: string) => {
  if (status === 'subscribed') return 'success'
  if (status === 'error') return 'exception'
  return undefined
}

const getLogType = (type: string) => {
  const types: Record<string, any> = {
    'success': 'success',
    'error': 'danger',
    'warning': 'warning'
  }
  return types[type] || 'info'
}

const formatTime = (datetime: string) => {
  if (!datetime) return '-'
  return new Date(datetime).toLocaleString('zh-CN')
}

const addLog = (message: string, type: string = 'info') => {
  logs.value.push({
    timestamp: new Date().toLocaleTimeString(),
    message,
    type
  })
}

onMounted(() => {
  loadAccounts()
  loadCards()
})
</script>
