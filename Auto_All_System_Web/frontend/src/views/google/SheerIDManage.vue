<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardHeader>
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <Icon><Check /></Icon>
            <CardTitle class="text-base">SheerID 验证管理</CardTitle>
          </div>
          <Button  variant="default" type="button" :disabled="loading" @click="loadAccounts">
            <Icon><Refresh /></Icon>
            <span class="ml-1.5">刷新列表</span>
          </Button>
        </div>
      </CardHeader>

      <CardContent class="space-y-6">
        <!-- 批量操作区 -->
        <div class="grid grid-cols-1 gap-4 md:grid-cols-12">
          <div class="md:col-span-6">
            <TextInput
              v-model="apiKey"
              type="password"
              placeholder="SheerID API Key"
              show-password
            >
              <template #prefix>
                <Icon><Key /></Icon>
              </template>
            </TextInput>
            <div class="mt-1 text-xs text-muted-foreground">用于批量验证 SheerID 链接</div>
          </div>

          <div class="md:col-span-3">
            <NumberInput
              v-model="threadCount"
              :min="1"
              :max="10"
              controls-position="right"
              class="w-full"
              placeholder="并发数"
            />
          </div>

          <div class="md:col-span-3">
            <Button
               variant="default" type="button"
              class="w-full"
              :disabled="!selectedAccounts.length || !apiKey || loading"
              :loading="loading"
              @click="startVerification"
            >
              <Icon><CircleCheck /></Icon>
              <span class="ml-1.5">批量验证选中</span>
            </Button>
          </div>
        </div>

        <!-- 统计面板 -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div class="rounded-xl bg-gradient-to-br from-sky-500 to-emerald-500 p-5 text-center text-white shadow-sm">
            <div class="text-3xl font-bold leading-none">{{ stats.link_ready }}</div>
            <div class="mt-1 text-sm text-white/90">待验证</div>
          </div>
          <div class="rounded-xl bg-gradient-to-br from-emerald-500 to-teal-400 p-5 text-center text-white shadow-sm">
            <div class="text-3xl font-bold leading-none">{{ stats.verified }}</div>
            <div class="mt-1 text-sm text-white/90">已验证</div>
          </div>
          <div class="rounded-xl bg-gradient-to-br from-amber-500 to-orange-400 p-5 text-center text-white shadow-sm">
            <div class="text-3xl font-bold leading-none">{{ stats.verifying }}</div>
            <div class="mt-1 text-sm text-white/90">验证中</div>
          </div>
          <div class="rounded-xl bg-gradient-to-br from-rose-500 to-amber-500 p-5 text-center text-white shadow-sm">
            <div class="text-3xl font-bold leading-none">{{ stats.failed }}</div>
            <div class="mt-1 text-sm text-white/90">验证失败</div>
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
          <DataColumn prop="email" label="邮箱" min-width="200">
            <template #default="{ row }">
              <Tag size="small">{{ row.email }}</Tag>
            </template>
          </DataColumn>
          <DataColumn prop="status" label="状态" width="120">
            <template #default="{ row }">
              <Tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </Tag>
            </template>
          </DataColumn>
          <DataColumn prop="verification_link" label="SheerID 链接" min-width="250">
            <template #default="{ row }">
              <div v-if="row.verification_link" class="max-w-[250px] truncate">
                <a :href="row.verification_link" target="_blank" class="text-primary hover:underline">
                  {{ row.verification_link }}
                </a>
              </div>
              <span v-else class="text-muted-foreground">未提取</span>
            </template>
          </DataColumn>
          <DataColumn prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.updated_at) }}
            </template>
          </DataColumn>
          <DataColumn label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <Button
                v-if="row.status === 'link_ready'"
                link
                 variant="default" type="button"
                :disabled="!apiKey"
                @click="verifySingle(row)"
              >
                <Icon><Check /></Icon>
              </Button>
              <Button link  variant="secondary" type="button" @click="showDetails(row)">
                <Icon><InfoFilled /></Icon>
              </Button>
            </template>
          </DataColumn>
        </DataTable>
      </CardContent>
    </Card>

    <!-- 日志对话框 -->
    <Modal
      v-model="logDialog"
      title="验证日志"
      width="800px"
    >
      <Scrollbar height="400px">
        <div v-for="(log, index) in logs" :key="index" class="border-b border-border p-2.5">
          <Tag :type="log.type === 'error' ? 'danger' : 'info'" size="small">
            {{ log.timestamp }}
          </Tag>
          <span class="ml-2 text-sm text-foreground">{{ log.message }}</span>
        </div>
        <div v-if="logs.length === 0" class="p-8 text-center">
          <div class="text-sm font-medium text-foreground">暂无日志</div>
          <div class="mt-1 text-xs text-muted-foreground">开始验证后会在这里显示过程记录</div>
        </div>
      </Scrollbar>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Check,
  Refresh,
  Key,
  CircleCheck,
  InfoFilled
} from '@/icons'
import { getGoogleAccounts, createGoogleTask } from '@/api/google_business'

interface Account {
  id: number
  email: string
  status: string
  verification_link?: string
  updated_at: string
}

interface Log {
  timestamp: string
  message: string
  type: string
}

const accounts = ref<Account[]>([])
const selectedAccounts = ref<Account[]>([])
const loading = ref(false)
const apiKey = ref('')
const threadCount = ref(3)
const logDialog = ref(false)
const logs = ref<Log[]>([])

const stats = reactive({
  link_ready: 0,
  verified: 0,
  verifying: 0,
  failed: 0
})

const loadAccounts = async () => {
  loading.value = true
  try {
    const response = await getGoogleAccounts({ status: 'link_ready' })
    accounts.value = (response as any) || []
    updateStats()
  } catch (error: any) {
    console.error('加载账号失败:', error)
    ElMessage.error('加载账号失败')
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  stats.link_ready = accounts.value.filter(a => a.status === 'link_ready').length
  stats.verified = accounts.value.filter(a => a.status === 'verified').length
  stats.verifying = accounts.value.filter(a => a.status === 'verifying').length
  stats.failed = 0
}

const handleSelectionChange = (selection: Account[]) => {
  selectedAccounts.value = selection
}

const startVerification = async () => {
  if (!selectedAccounts.value.length) {
    ElMessage.warning('请选择要验证的账号')
    return
  }

  loading.value = true
  logs.value = []
  logDialog.value = true

  try {
    for (const account of selectedAccounts.value) {
      addLog(`开始验证: ${account.email}`)

      try {
        await createGoogleTask({
          task_type: 'verify_sheerid',
          account_ids: [account.id],
          config: {
            api_key: apiKey.value,
            thread_count: threadCount.value
          }
        })
        addLog(`✅ ${account.email} 验证任务已创建`, 'success')
      } catch (error: any) {
        addLog(`❌ ${account.email} 验证失败: ${error.message}`, 'error')
      }

      await new Promise(resolve => setTimeout(resolve, 1000))
    }

    addLog('批量验证完成')
    ElMessage.success('批量验证任务已提交')
    await loadAccounts()
  } catch (error: any) {
    addLog(`验证过程出错: ${error.message}`, 'error')
  } finally {
    loading.value = false
  }
}

const verifySingle = async (account: Account) => {
  loading.value = true
  try {
    await createGoogleTask({
      task_type: 'verify_sheerid',
      account_ids: [account.id],
      config: {
        api_key: apiKey.value
      }
    })
    ElMessage.success(`验证任务已创建: ${account.email}`)
    await loadAccounts()
  } catch (error: any) {
    ElMessage.error(`验证失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const showDetails = (account: Account) => {
  ElMessageBox.alert(
    `<pre>${JSON.stringify(account, null, 2)}</pre>`,
    '账号详情',
    {
      dangerouslyUseHTMLString: true
    }
  )
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    'link_ready': 'info',
    'verified': 'success',
    'verifying': 'warning',
    'failed': 'danger',
    'ineligible': 'info'
  }
  return types[status] || ''
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'link_ready': '待验证',
    'verified': '已验证',
    'verifying': '验证中',
    'failed': '验证失败',
    'ineligible': '无资格',
    'pending_check': '待检测',
    'subscribed': '已订阅'
  }
  return texts[status] || status
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
})
</script>
