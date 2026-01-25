<template>
  <div class="sheerid-module">
    <div class="module-header">
      <h2>SheerID验证</h2>
    </div>

    <el-card shadow="hover">
      <el-alert
        title="SheerID学生身份验证将自动填写学生信息并提交验证"
        type="info"
        :closable="false"
        class="mb-4"
      />

      <el-form :model="sheeridForm" label-width="120px">
        <el-form-item label="选择账号">
          <el-select v-model="sheeridForm.accounts" multiple placeholder="请选择要验证的账号" style="width: 100%">
            <el-option
              v-for="account in availableAccounts"
              :key="account.id"
              :label="account.email"
              :value="account.id"
              :disabled="account.sheerid_verified"
            >
              <span>{{ account.email }}</span>
              <el-tag v-if="account.sheerid_verified" size="small" type="success" class="ml-2">已验证</el-tag>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="学生信息">
          <el-input v-model="sheeridForm.studentName" placeholder="学生姓名" class="mb-2" />
          <el-input v-model="sheeridForm.studentEmail" placeholder="学生邮箱" class="mb-2" />
          <el-input v-model="sheeridForm.schoolName" placeholder="学校名称" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" @click="startVerification" :loading="verifying">
            <el-icon><Check /></el-icon>
            开始验证
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 验证结果 -->
    <el-card shadow="hover" class="mt-4" v-if="verificationResults.length > 0">
      <template #header>
        <span class="card-header">验证结果</span>
      </template>
      <el-table :data="verificationResults" stripe>
        <el-table-column prop="email" label="账号" width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'">
              {{ row.success ? '验证成功' : '验证失败' }}
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
import { Check } from '@element-plus/icons-vue'
import { googleAccountsApi, googleTasksApi } from '@/api/google'
import type { GoogleAccount } from '@/types'

const verifying = ref(false)
const availableAccounts = ref<GoogleAccount[]>([])
const verificationResults = ref<any[]>([])
const currentTaskId = ref<number | null>(null)
const pollingTimer = ref<number | null>(null)

const sheeridForm = reactive({
  accounts: [] as number[],
  studentName: '',
  studentEmail: '',
  schoolName: ''
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

const startVerification = async () => {
  if (sheeridForm.accounts.length === 0) {
    ElMessage.warning('请至少选择一个账号')
    return
  }

  if (!sheeridForm.studentName || !sheeridForm.studentEmail || !sheeridForm.schoolName) {
    ElMessage.warning('请填写完整的学生信息')
    return
  }

  verifying.value = true
  verificationResults.value = []

  try {
    // 调用后端API创建SheerID验证任务
    const response = await googleTasksApi.createTask({
      task_type: 'verify',
      account_ids: sheeridForm.accounts,
      config: {
        student_name: sheeridForm.studentName,
        student_email: sheeridForm.studentEmail,
        school_name: sheeridForm.schoolName
      }
    })

    if (response.success && response.task_id) {
      currentTaskId.value = response.task_id
      ElMessage.success(`任务已创建，任务ID: ${response.task_id}`)
      
      // 开始轮询任务状态
      startPolling(response.task_id)
    } else {
      throw new Error(response.error || response.message || '任务创建失败')
    }
  } catch (error: any) {
    verifying.value = false
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
          const email = acc.account_email || availableAccounts.value.find(a => a.id === accountId)?.email || `账号${accountId}`

          // 检查是否已经有这个账号的最终结果
          const existingResult = verificationResults.value.find(r => r.email === email)
          if (existingResult) continue

          if (acc.status === 'success' || acc.status === 'failed' || acc.status === 'skipped') {
            verificationResults.value.push({
              email,
              success: acc.status === 'success',
              message: acc.result_message || (acc.status === 'success' ? 'SheerID验证通过' : `验证失败: ${acc.error_message || '未知错误'}`),
              time: new Date().toLocaleTimeString()
            })
          }
        }
      }

      // 检查任务是否完成
      if (taskInfo.status === 'completed' || taskInfo.status === 'failed' || taskInfo.status === 'cancelled') {
        stopPolling()
        verifying.value = false
        
        if (taskInfo.status === 'completed') {
          ElMessage.success(`验证完成！成功: ${taskInfo.success_count}, 失败: ${taskInfo.failed_count}`)
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

onMounted(() => {
  fetchAvailableAccounts()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped lang="scss">
.sheerid-module {
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

  .mb-2 {
    margin-bottom: 8px;
  }

  .mt-4 {
    margin-top: 24px;
  }

  .ml-2 {
    margin-left: 8px;
  }

  .card-header {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
  }
}
</style>
