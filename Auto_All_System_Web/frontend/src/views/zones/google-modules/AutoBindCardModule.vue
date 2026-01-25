<template>
  <div class="auto-bind-card-module">
    <div class="module-header">
      <h2>自动绑卡</h2>
    </div>

    <el-card shadow="hover">
      <el-alert
        title="自动绑卡功能将自动为已验证的账号绑定虚拟卡并完成订阅"
        type="info"
        :closable="false"
        class="mb-4"
      />

      <el-form :model="bindForm" label-width="120px">
        <el-form-item label="选择账号">
          <el-select v-model="bindForm.accounts" multiple placeholder="请选择要绑卡的账号" style="width: 100%">
            <el-option
              v-for="account in verifiedAccounts"
              :key="account.id"
              :label="account.email"
              :value="account.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="卡池选择">
          <el-radio-group v-model="bindForm.cardPool">
            <el-radio label="public">公共卡池</el-radio>
            <el-radio label="private">私有卡池</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="绑卡策略">
          <el-radio-group v-model="bindForm.strategy">
            <el-radio label="sequential">顺序分配</el-radio>
            <el-radio label="random">随机选择</el-radio>
            <el-radio label="least_used">最少使用优先</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" @click="startBinding" :loading="binding">
            <el-icon><CreditCard /></el-icon>
            开始绑卡
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 绑卡结果 -->
    <el-card shadow="hover" class="mt-4" v-if="bindingResults.length > 0">
      <template #header>
        <span class="card-header">绑卡结果</span>
      </template>
      <el-table :data="bindingResults" stripe>
        <el-table-column prop="email" label="账号" width="200" />
        <el-table-column prop="cardNumber" label="卡号" width="180">
          <template #default="{ row }">
            {{ maskCardNumber(row.cardNumber) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'">
              {{ row.success ? '绑卡成功' : '绑卡失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" />
        <el-table-column prop="time" label="时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { CreditCard } from '@element-plus/icons-vue'
import { googleAccountsApi, googleTasksApi } from '@/api/google'
import type { GoogleAccount } from '@/types'

const binding = ref(false)
const verifiedAccounts = ref<GoogleAccount[]>([])
const bindingResults = ref<any[]>([])
const currentTaskId = ref<number | null>(null)
const pollingTimer = ref<number | null>(null)

const bindForm = reactive({
  accounts: [] as number[],
  cardPool: 'public',
  strategy: 'sequential'
})

const fetchVerifiedAccounts = async () => {
  try {
    const response = await googleAccountsApi.getAccounts({ 
      sheerid_verified: true,
      page_size: 100 
    })
    // 兼容后端返回数组或分页对象两种情况
    if (Array.isArray(response)) {
      verifiedAccounts.value = response
    } else if (response.results) {
      verifiedAccounts.value = response.results
    } else {
      verifiedAccounts.value = []
    }
  } catch (error) {
    ElMessage.error('获取已验证账号失败')
  }
}

const startBinding = async () => {
  if (bindForm.accounts.length === 0) {
    ElMessage.warning('请至少选择一个账号')
    return
  }

  binding.value = true
  bindingResults.value = []

  try {
    // 调用后端API创建绑卡任务
    const response = await googleTasksApi.createTask({
      task_type: 'bind_card',
      account_ids: bindForm.accounts,
      config: {
        card_pool: bindForm.cardPool,
        card_strategy: bindForm.strategy
      }
    })

    if (response.success && response.task_id) {
      currentTaskId.value = response.task_id
      ElMessage.success(`任务已创建，任务ID: ${response.task_id}，预计费用: ${response.estimated_cost || 0} 积分`)
      
      // 开始轮询任务状态
      startPolling(response.task_id)
    } else {
      throw new Error(response.error || response.message || '任务创建失败')
    }
  } catch (error: any) {
    binding.value = false
    const errorMsg = error.response?.data?.error || error.message || '任务创建失败'
    ElMessage.error(errorMsg)
  }
}

const startPolling = (taskId: number) => {
  // 每2秒轮询一次任务状态
  pollingTimer.value = window.setInterval(async () => {
    try {
      const taskInfo = await googleTasksApi.getTask(taskId)
      
      // 获取任务账号列表更新详细进度
      const accountsInfo = await googleTasksApi.getTaskAccounts(taskId)
      if (accountsInfo.accounts) {
        for (const acc of accountsInfo.accounts) {
          const accountId = acc.account ?? acc.account_id
          const email = acc.account_email || verifiedAccounts.value.find(a => a.id === accountId)?.email || `账号${accountId}`

          // 检查是否已经有这个账号的结果
          const existingResult = bindingResults.value.find(r => r.email === email)
          if (existingResult) continue

          if (acc.status === 'success' || acc.status === 'failed' || acc.status === 'skipped') {
            const last4 = typeof acc.result_message === 'string'
              ? (acc.result_message.match(/\*\*\*\*(\d{4})/)?.[1] || '')
              : ''

            bindingResults.value.push({
              email,
              cardNumber: last4 || '****',
              success: acc.status === 'success',
              message: acc.result_message || (acc.status === 'success' ? '虚拟卡绑定成功，订阅已激活' : `绑卡失败: ${acc.error_message || '未知错误'}`),
              time: new Date().toLocaleTimeString()
            })
          }
        }
      }

      // 检查任务是否完成
      if (taskInfo.status === 'completed' || taskInfo.status === 'failed' || taskInfo.status === 'cancelled') {
        stopPolling()
        binding.value = false
        
        if (taskInfo.status === 'completed') {
          ElMessage.success(`绑卡完成！成功: ${taskInfo.success_count}, 失败: ${taskInfo.failed_count}`)
        } else if (taskInfo.status === 'failed') {
          ElMessage.error('任务执行失败')
        } else {
          ElMessage.warning('任务已取消')
        }
      }
    } catch (error) {
      console.error('轮询任务状态失败:', error)
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollingTimer.value) {
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }
}

const maskCardNumber = (cardNumber: string) => {
  if (!cardNumber || cardNumber.length < 4) return '****'
  return `**** **** **** ${cardNumber.slice(-4)}`
}

onMounted(() => {
  fetchVerifiedAccounts()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.auto-bind-card-module {
  .module-header {
    margin-bottom: 20px;

    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: #303133;
    }
  }

  .mb-4 {
    margin-bottom: 16px;
  }

  .mt-4 {
    margin-top: 24px;
  }

  .card-header {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
  }
}
</style>
