<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm">
      <CardHeader>
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <Icon><CreditCard /></Icon>
            <CardTitle class="text-base">自动绑卡订阅</CardTitle>
          </div>
          <Button  variant="default" type="button" :disabled="loading" @click="loadData">
            <Icon><Refresh /></Icon>
            <span class="ml-1.5">刷新</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent class="space-y-6">
        <!-- 配置区域 -->
        <div class="grid grid-cols-1 gap-4 md:grid-cols-12">
          <div class="md:col-span-4">
            <NumberInput
              v-model="config.cardsPerAccount"
              :min="1"
              :max="100"
              controls-position="right"
              class="w-full"
            >
              <template #prefix>
                一卡几绑
              </template>
            </NumberInput>
            <div class="mt-1 text-xs text-muted-foreground">一张卡可以绑定多少个账号</div>
          </div>

          <div class="md:col-span-4">
            <NumberInput
              v-model="config.threadCount"
              :min="1"
              :max="20"
              controls-position="right"
              class="w-full"
            >
              <template #prefix>
                并发数
              </template>
            </NumberInput>
            <div class="mt-1 text-xs text-muted-foreground">同时处理的账号数量</div>
          </div>

          <div class="md:col-span-4">
            <FileUpload
              action="#"
              :before-upload="uploadCards"
              :show-file-list="false"
              accept=".txt"
            >
              <Button  variant="default" type="button" :loading="uploading" class="w-full">
                <Icon><Upload /></Icon>
                <span class="ml-1.5">上传卡片文件</span>
              </Button>
            </FileUpload>
            <div class="mt-1 text-xs text-muted-foreground">格式: cards.txt (每行一张卡)</div>
          </div>
        </div>

        <!-- 延迟设置 -->
        <Collapse v-model="activeCollapse">
          <CollapseItem title="延迟设置（秒）" name="delays">
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
              <SimpleFormItem label="点击 Offer 后">
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
        </Collapse>

        <!-- 统计信息 -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div class="rounded-xl border border-border bg-background/60 p-4 shadow-sm">
            <Statistic title="可用卡片" :value="stats.availableCards">
              <template #prefix>
                <Icon><Tickets /></Icon>
              </template>
            </Statistic>
          </div>
          <div class="rounded-xl border border-border bg-background/60 p-4 shadow-sm">
            <Statistic title="已验证账号" :value="stats.verifiedAccounts">
              <template #prefix>
                <Icon><User /></Icon>
              </template>
            </Statistic>
          </div>
          <div class="rounded-xl border border-border bg-background/60 p-4 shadow-sm">
            <Statistic title="待绑卡" :value="stats.pendingBindCard">
              <template #prefix>
                <Icon><Clock /></Icon>
              </template>
            </Statistic>
          </div>
          <div class="rounded-xl border border-border bg-background/60 p-4 shadow-sm">
            <Statistic title="已订阅" :value="stats.subscribed">
              <template #prefix>
                <Icon><CircleCheck /></Icon>
              </template>
            </Statistic>
          </div>
        </div>

        <!-- 账号列表 -->
        <DataTable
          :data="accounts"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          stripe
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
          <DataColumn prop="assigned_card" label="已分配卡片" width="150">
            <template #default="{ row }">
              <code
                v-if="row.assigned_card"
                class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-primary"
              >
                {{ row.assigned_card }}
              </code>
              <span v-else class="text-muted-foreground">未分配</span>
            </template>
          </DataColumn>
          <DataColumn prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.updated_at) }}
            </template>
          </DataColumn>
        </DataTable>

        <!-- 操作按钮 -->
        <div class="flex flex-col items-stretch justify-center gap-3 pt-2 sm:flex-row sm:items-center">
          <Button
             variant="default" type="button"
            size="large"
            class="w-full sm:w-auto"
            :disabled="!selectedAccounts.length || loading"
            :loading="loading"
            @click="startBinding"
          >
            <Icon><CircleCheck /></Icon>
            <span class="ml-1.5">开始绑卡订阅</span>
          </Button>
          <Button
             variant="secondary" type="button"
            size="large"
            class="w-full sm:w-auto"
            :disabled="loading"
            @click="stopBinding"
          >
            <Icon><CircleClose /></Icon>
            <span class="ml-1.5">停止任务</span>
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- 进度对话框 -->
    <Modal
      v-model="progressDialog"
      title="绑卡进度"
      width="700px"
      :close-on-click-modal="false"
    >
      <ProgressBar
        :percentage="progress"
        :status="progressStatus"
        :stroke-width="20"
      />
      <div class="mt-4 space-y-1 text-center text-sm text-muted-foreground">
        <p>当前: {{ currentAccount }}</p>
        <p>进度: {{ completedCount }} / {{ totalCount }}</p>
      </div>

      <Scrollbar height="300px" class="mt-5">
        <div v-for="(log, index) in logs" :key="index" class="border-b border-border p-2.5">
          <Tag :type="log.type === 'error' ? 'danger' : 'info'" size="small">
            {{ log.timestamp }}
          </Tag>
          <span class="ml-2 text-sm text-foreground">{{ log.message }}</span>
        </div>
      </Scrollbar>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  CreditCard,
  Refresh,
  Upload,
  Tickets,
  User,
  Clock,
  CircleCheck,
  CircleClose
} from '@/icons'
import { getGoogleAccounts, createGoogleTask, uploadGoogleCards } from '@/api/google_business'

interface Account {
  id: number
  email: string
  status: string
  assigned_card?: string
  updated_at: string
}

const accounts = ref<Account[]>([])
const selectedAccounts = ref<Account[]>([])
const loading = ref(false)
const uploading = ref(false)
const progressDialog = ref(false)
const activeCollapse = ref<string[]>([])

const config = reactive({
  cardsPerAccount: 5,
  threadCount: 3,
  delays: {
    afterOffer: 5,
    afterAddCard: 3,
    afterSave: 5,
    afterSubscribe: 3
  }
})

const stats = reactive({
  availableCards: 0,
  verifiedAccounts: 0,
  pendingBindCard: 0,
  subscribed: 0
})

const progress = ref(0)
const progressStatus = ref<'success' | 'exception' | 'warning' | ''>('')
const currentAccount = ref('')
const completedCount = ref(0)
const totalCount = ref(0)
const logs = ref<any[]>([])

const loadData = async () => {
  loading.value = true
  try {
    const response = await getGoogleAccounts({ status: 'verified' })
    const accountsList = (response as any) || []
    accounts.value = accountsList
    stats.verifiedAccounts = accountsList.filter((a: Account) => a.status === 'verified').length
    stats.subscribed = accountsList.filter((a: Account) => a.status === 'subscribed').length
    stats.pendingBindCard = stats.verifiedAccounts - stats.subscribed
  } catch (error: any) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection: Account[]) => {
  selectedAccounts.value = selection
}

const uploadCards = (file: File) => {
  uploading.value = true
  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const content = e.target?.result as string
      const cards = content.split('\n').filter(line => line.trim())
      
      await uploadGoogleCards(cards)
      ElMessage.success(`成功上传 ${cards.length} 张卡片`)
      stats.availableCards = cards.length
    } catch (error: any) {
      ElMessage.error('上传失败')
    } finally {
      uploading.value = false
    }
  }
  reader.readAsText(file)
  return false
}

const startBinding = async () => {
  if (!selectedAccounts.value.length) {
    ElMessage.warning('请选择要绑卡的账号')
    return
  }

  loading.value = true
  progressDialog.value = true
  logs.value = []
  progress.value = 0
  completedCount.value = 0
  totalCount.value = selectedAccounts.value.length

  try {
    const accountIds = selectedAccounts.value.map(a => a.id)
    await createGoogleTask({
      task_type: 'bind_card',
      account_ids: accountIds,
      config: {
        cards_per_account: config.cardsPerAccount,
        thread_count: config.threadCount,
        delays: config.delays
      }
    })
    
    ElMessage.success('绑卡任务已创建')
    progressStatus.value = 'success'
    progress.value = 100
  } catch (error: any) {
    ElMessage.error('任务创建失败')
    progressStatus.value = 'exception'
  } finally {
    loading.value = false
  }
}

const stopBinding = () => {
  ElMessage.info('停止任务功能开发中')
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    'verified': 'warning',
    'subscribed': 'success',
    'binding': 'primary',
    'error': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'verified': '已验证未绑卡',
    'subscribed': '已订阅',
    'binding': '绑卡中',
    'error': '错误'
  }
  return texts[status] || status
}

const formatTime = (datetime: string) => {
  if (!datetime) return '-'
  return new Date(datetime).toLocaleString('zh-CN')
}

onMounted(() => {
  loadData()
})
</script>
