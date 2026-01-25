<template>
  <div class="one-click-auto-module">
    <div class="module-header">
      <h2>一键全自动</h2>
    </div>

    <el-card shadow="hover">
      <el-alert
        title="一键全自动功能将自动完成：SheerID验证 → 自动绑卡 → 订阅确认"
        type="info"
        :closable="false"
        class="mb-4"
      />

      <el-form :model="autoForm" label-width="120px">
        <el-form-item label="选择账号">
          <el-select v-model="autoForm.accounts" multiple placeholder="请选择要处理的账号" style="width: 100%">
            <el-option
              v-for="account in availableAccounts"
              :key="account.id"
              :label="account.email"
              :value="account.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="处理模式">
          <el-radio-group v-model="autoForm.mode">
            <el-radio label="sequential">顺序执行</el-radio>
            <el-radio label="parallel">并行执行</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="失败重试">
          <el-switch v-model="autoForm.retry" />
          <span class="ml-2">启用失败自动重试</span>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" @click="startAutoProcess" :loading="processing">
            <el-icon><Cpu /></el-icon>
            开始自动处理
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 处理进度 -->
    <el-card shadow="hover" class="mt-4" v-if="processing || processResults.length > 0">
      <template #header>
        <div class="card-header">
          <span>处理进度</span>
          <el-progress :percentage="overallProgress" :status="progressStatus" style="flex: 1; margin-left: 20px;" />
        </div>
      </template>

      <el-timeline>
        <el-timeline-item
          v-for="(result, index) in processResults"
          :key="index"
          :type="result.status"
          :timestamp="result.time"
        >
          {{ result.message }}
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu } from '@element-plus/icons-vue'
import { googleAccountsApi, googleTasksApi } from '@/api/google'
import type { GoogleAccount } from '@/types'

const processing = ref(false)
const availableAccounts = ref<GoogleAccount[]>([])
const currentTaskId = ref<number | null>(null)
const pollingTimer = ref<number | null>(null)

const autoForm = reactive({
  accounts: [] as number[],
  mode: 'sequential',
  retry: true
})

const processResults = ref<any[]>([])
const overallProgress = ref(0)

const progressStatus = computed(() => {
  if (overallProgress.value === 100) return 'success'
  if (processing.value) return undefined
  return 'exception'
})

const fetchAvailableAccounts = async () => {
  try {
    const response = await googleAccountsApi.getAccounts({ page_size: 100 })
    // 兼容后端返回数组或分页对象两种情况
    if (Array.isArray(response)) {
      availableAccounts.value = response
    } else if (response.results) {
      availableAccounts.value = response.results
    } else {
      availableAccounts.value = []
    }
  } catch (error) {
    ElMessage.error('获取账号列表失败')
  }
}

const startAutoProcess = async () => {
  if (autoForm.accounts.length === 0) {
    ElMessage.warning('请至少选择一个账号')
    return
  }

  processing.value = true
  processResults.value = []
  overallProgress.value = 0

  try {
    // 添加初始日志
    processResults.value.push({
      status: 'primary',
      time: new Date().toLocaleTimeString(),
      message: `正在创建一键全自动任务，共 ${autoForm.accounts.length} 个账号...`
    })

    // 调用后端API创建一键全自动任务
    const response = await googleTasksApi.createTask({
      task_type: 'one_click',
      account_ids: autoForm.accounts,
      config: {
        mode: autoForm.mode,
        retry_on_fail: autoForm.retry,
        max_concurrency: autoForm.mode === 'parallel' ? 3 : 1
      }
    })

    if (response.success && response.task_id) {
      currentTaskId.value = response.task_id
      
      processResults.value.push({
        status: 'success',
        time: new Date().toLocaleTimeString(),
        message: `任务已创建，任务ID: ${response.task_id}，预计费用: ${response.estimated_cost || 0} 积分`
      })

      // 开始轮询任务状态
      startPolling(response.task_id)
    } else {
      throw new Error(response.error || response.message || '任务创建失败')
    }
  } catch (error: any) {
    processing.value = false
    const errorMsg = error.response?.data?.error || error.message || '任务创建失败'
    processResults.value.push({
      status: 'danger',
      time: new Date().toLocaleTimeString(),
      message: `错误: ${errorMsg}`
    })
    ElMessage.error(errorMsg)
  }
}

const startPolling = (taskId: number) => {
  // 每2秒轮询一次任务状态
  pollingTimer.value = window.setInterval(async () => {
    try {
      const taskInfo = await googleTasksApi.getTask(taskId)
      
      // 更新进度
      if (taskInfo.total_count > 0) {
        const completed = (taskInfo.success_count || 0) + (taskInfo.failed_count || 0) + (taskInfo.skipped_count || 0)
        overallProgress.value = Math.round((completed / taskInfo.total_count) * 100)
      }

      // 获取任务账号列表更新详细进度
      const accountsInfo = await googleTasksApi.getTaskAccounts(taskId)
      if (accountsInfo.accounts) {
        for (const acc of accountsInfo.accounts) {
          const accountId = acc.account ?? acc.account_id
          const email = acc.account_email || availableAccounts.value.find(a => a.id === accountId)?.email || `账号${accountId}`

          // 检查是否已经有这个账号的最终结果
          const existingResult = processResults.value.find(
            r => r.email === email && (r.finalStatus === 'success' || r.finalStatus === 'failed' || r.finalStatus === 'skipped')
          )
          if (existingResult) continue

          if (acc.status === 'processing') {
            // 更新或添加运行中状态
            const runningIdx = processResults.value.findIndex(
              r => r.email === email && r.isRunning
            )
            if (runningIdx === -1) {
              processResults.value.push({
                status: 'primary',
                time: new Date().toLocaleTimeString(),
                message: `正在处理: ${email}`,
                email,
                isRunning: true
              })
            }
          } else if (acc.status === 'success') {
            processResults.value.push({
              status: 'success',
              time: new Date().toLocaleTimeString(),
              message: `${email} - ${acc.result_message || '处理完成'}`,
              email,
              finalStatus: 'success'
            })
          } else if (acc.status === 'failed') {
            processResults.value.push({
              status: 'danger',
              time: new Date().toLocaleTimeString(),
              message: `${email} - 失败: ${acc.error_message || '未知错误'}`,
              email,
              finalStatus: 'failed'
            })
          } else if (acc.status === 'skipped') {
            processResults.value.push({
              status: 'warning',
              time: new Date().toLocaleTimeString(),
              message: `${email} - 已跳过: ${acc.result_message || ''}`,
              email,
              finalStatus: 'skipped'
            })
          }
        }
      }

      // 检查任务是否完成
      if (taskInfo.status === 'completed' || taskInfo.status === 'failed' || taskInfo.status === 'cancelled') {
        stopPolling()
        processing.value = false
        overallProgress.value = 100

        if (taskInfo.status === 'completed') {
          processResults.value.push({
            status: 'success',
            time: new Date().toLocaleTimeString(),
            message: `全部处理完成！成功: ${taskInfo.success_count}, 失败: ${taskInfo.failed_count}`
          })
          ElMessage.success('全部处理完成！')
        } else if (taskInfo.status === 'failed') {
          processResults.value.push({
            status: 'danger',
            time: new Date().toLocaleTimeString(),
            message: `任务失败: ${taskInfo.error_message || '未知错误'}`
          })
          ElMessage.error('任务执行失败')
        } else {
          processResults.value.push({
            status: 'warning',
            time: new Date().toLocaleTimeString(),
            message: '任务已取消'
          })
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

onMounted(() => {
  fetchAvailableAccounts()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.one-click-auto-module {
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

  .ml-2 {
    margin-left: 8px;
    color: #606266;
  }

  .card-header {
    display: flex;
    align-items: center;
    font-size: 18px;
    font-weight: 600;
    color: #303133;
  }
}
</style>
