<template>
  <div class="subscription-module">
    <div class="module-header">
      <h2>📋 订阅状态验证</h2>
    </div>

    <el-card shadow="hover">
      <el-alert
        title="订阅验证功能可以批量检测账号的订阅状态，并支持自动截图保存"
        type="info"
        :closable="false"
        class="mb-4"
      />

      <el-form :model="subscriptionForm" label-width="120px">
        <el-form-item label="选择账号">
          <el-select v-model="subscriptionForm.accounts" multiple placeholder="请选择账号" style="width: 100%">
            <el-option
              v-for="account in availableAccounts"
              :key="account.id"
              :label="account.email"
              :value="account.id"
            >
              <div class="account-option">
                <span>{{ account.email }}</span>
                <el-tag v-if="account.status" size="small" :type="getStatusType(account.status)">
                  {{ getStatusLabel(account.status) }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="选项">
          <el-checkbox v-model="subscriptionForm.takeScreenshot">保存截图</el-checkbox>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" @click="verifyStatus" :loading="processing">
            <el-icon><View /></el-icon>
            验证状态
          </el-button>
          <el-button type="success" size="large" @click="clickSubscribe" :loading="subscribing">
            <el-icon><CircleCheck /></el-icon>
            点击订阅
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 验证结果 -->
    <el-card shadow="hover" class="mt-4" v-if="verifyResults.length > 0">
      <template #header>
        <span class="card-header">验证结果</span>
      </template>
      <el-table :data="verifyResults" stripe>
        <el-table-column prop="email" label="账号" width="200" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status?.status)">
              {{ getStatusLabel(row.status?.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="截图" width="120">
          <template #default="{ row }">
            <el-button v-if="row.screenshot" size="small" @click="viewScreenshot(row.screenshot)">
              查看
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作结果">
          <template #default="{ row }">
            {{ row.success ? '成功' : '失败' }}
            <span v-if="row.message" class="text-muted"> - {{ row.message }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 截图预览 -->
    <el-dialog v-model="screenshotDialogVisible" title="截图预览" width="800">
      <img :src="currentScreenshot" alt="Screenshot" style="max-width: 100%;" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { View, CircleCheck } from '@element-plus/icons-vue'
import { googleAccountsApi, googleSubscriptionApi, googleCeleryTasksApi } from '@/api/google'
import type { GoogleAccount } from '@/types'

const processing = ref(false)
const subscribing = ref(false)
const availableAccounts = ref<GoogleAccount[]>([])
const verifyResults = ref<any[]>([])
const pollingTimer = ref<number | null>(null)
const currentTaskId = ref<string>('')

const screenshotDialogVisible = ref(false)
const currentScreenshot = ref('')
const currentScreenshotObjectUrl = ref<string | null>(null)

const subscriptionForm = reactive({
  accounts: [] as number[],
  takeScreenshot: true,
})

onMounted(async () => {
  await loadAccounts()
})

onBeforeUnmount(() => {
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }

  if (currentScreenshotObjectUrl.value) {
    URL.revokeObjectURL(currentScreenshotObjectUrl.value)
    currentScreenshotObjectUrl.value = null
  }
})

async function loadAccounts() {
  try {
    const response = await googleAccountsApi.getAccounts({ page_size: 100 })

    // 兼容后端返回数组或分页对象两种情况
    if (Array.isArray(response)) {
      availableAccounts.value = response
    } else if (response?.results) {
      availableAccounts.value = response.results
    } else {
      availableAccounts.value = []
    }
  } catch (error) {
    console.error('Failed to load accounts:', error)
    ElMessage.error('加载账号列表失败')
  }
}

async function verifyStatus() {
  if (subscriptionForm.accounts.length === 0) {
    ElMessage.warning('请选择至少一个账号')
    return
  }

  processing.value = true
  verifyResults.value = []

  try {
    const response = await googleSubscriptionApi.verifyStatus({
      account_ids: subscriptionForm.accounts,
      take_screenshot: subscriptionForm.takeScreenshot,
    })

    if (!response || !response.task_id) {
      throw new Error(response?.error || response?.message || '任务提交失败')
    }

    ElMessage.success(`验证任务已提交，任务ID: ${response.task_id}`)
    pollTaskStatus(String(response.task_id))
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '任务提交失败')
    processing.value = false
  } finally {
    // processing 在轮询结束时置回 false
  }
}

async function clickSubscribe() {
  if (subscriptionForm.accounts.length === 0) {
    ElMessage.warning('请选择至少一个账号')
    return
  }

  subscribing.value = true

  try {
    const response = await googleSubscriptionApi.clickSubscribe({
      account_ids: subscriptionForm.accounts,
    })

    if (!response || !response.task_id) {
      throw new Error(response?.error || response?.message || '任务提交失败')
    }

    ElMessage.success(`订阅任务已提交，任务ID: ${response.task_id}`)
    pollTaskStatus(String(response.task_id))
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '任务提交失败')
    subscribing.value = false
  } finally {
    // subscribing 在轮询结束时置回 false
  }
}

async function pollTaskStatus(taskId: string) {
  currentTaskId.value = taskId

  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }

  const pollOnce = async () => {
    const status = await googleCeleryTasksApi.getTask(taskId)

    if (status.state === 'PROGRESS') {
      return
    }

    if (status.state === 'SUCCESS') {
      const res = status.result || {}
      const rawResults: any[] = Array.isArray(res.results) ? res.results : []

      verifyResults.value = rawResults.map((r) => {
        const statusObj = r.status || (r.final_status ? { status: r.final_status } : null)
        const screenshot = r.screenshot || null

        return {
          email: r.email || 'unknown',
          success: Boolean(r.success),
          message: r.message || '',
          status: statusObj,
          screenshot,
        }
      })

      if (pollingTimer.value) {
        window.clearInterval(pollingTimer.value)
        pollingTimer.value = null
      }

      processing.value = false
      subscribing.value = false
      return
    }

    if (status.state === 'FAILURE') {
      if (pollingTimer.value) {
        window.clearInterval(pollingTimer.value)
        pollingTimer.value = null
      }

      processing.value = false
      subscribing.value = false
      ElMessage.error(status.error || '任务执行失败')
    }
  }

  try {
    await pollOnce()
  } catch (e: any) {
    processing.value = false
    subscribing.value = false
    ElMessage.error(e?.message || '任务状态查询失败')
    return
  }

  pollingTimer.value = window.setInterval(async () => {
    try {
      await pollOnce()
    } catch (e: any) {
      console.error('pollTaskStatus failed:', e)
    }
  }, 2000)
}

function getStatusType(status: string): string {
  const types: Record<string, string> = {
    subscribed: 'success',
    verified: 'primary',
    link_ready: 'warning',
    ineligible: 'danger',
    pending_check: 'info',
    unknown: 'info',
  }
  return types[status] || 'info'
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    subscribed: '已订阅',
    verified: '已验证',
    link_ready: '待验证',
    ineligible: '无资格',
    pending_check: '待检测',
    unknown: '未知',
  }
  return labels[status] || status || '未知'
}

function viewScreenshot(path: string) {
  ;(async () => {
    try {
      const parts = String(path).split(/[\\/]/)
      const filename = parts[parts.length - 1]

      // 清理旧的 object url
      if (currentScreenshotObjectUrl.value) {
        URL.revokeObjectURL(currentScreenshotObjectUrl.value)
        currentScreenshotObjectUrl.value = null
      }

      const blob = await googleSubscriptionApi.getScreenshot(filename)
      const objectUrl = URL.createObjectURL(blob)
      currentScreenshotObjectUrl.value = objectUrl
      currentScreenshot.value = objectUrl
      screenshotDialogVisible.value = true
    } catch (e: any) {
      console.error('viewScreenshot failed:', e)
      ElMessage.error(e?.message || '截图加载失败')
    }
  })()
}
</script>

<style scoped lang="scss">
.subscription-module {
  .module-header {
    margin-bottom: 16px;
    h2 {
      margin: 0;
      font-size: 20px;
    }
  }

  .mb-4 {
    margin-bottom: 16px;
  }

  .mt-4 {
    margin-top: 16px;
  }

  .account-option {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .text-muted {
    color: #909399;
    font-size: 12px;
  }
}
</style>
