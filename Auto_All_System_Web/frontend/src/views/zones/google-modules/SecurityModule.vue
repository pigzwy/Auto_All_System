<template>
  <div class="security-module">
    <div class="module-header">
      <h2>🔐 安全设置</h2>
    </div>

    <el-card shadow="hover">
      <el-alert
        title="安全设置功能可以批量修改账号的 2FA 密钥、辅助邮箱，以及获取备份验证码"
        type="info"
        :closable="false"
        class="mb-4"
      />

      <el-form :model="securityForm" label-width="120px">
        <el-form-item label="选择账号">
          <el-select v-model="securityForm.accounts" multiple placeholder="请选择账号" style="width: 100%">
            <el-option
              v-for="account in availableAccounts"
              :key="account.id"
              :label="account.email"
              :value="account.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="操作类型">
          <el-radio-group v-model="securityForm.action">
            <el-radio label="change_2fa">修改 2FA 密钥</el-radio>
            <el-radio label="change_email">修改辅助邮箱</el-radio>
            <el-radio label="get_backup_codes">获取备份验证码</el-radio>
            <el-radio label="one_click">一键修改全部</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="securityForm.action === 'change_email' || securityForm.action === 'one_click'" label="新辅助邮箱">
          <el-input v-model="securityForm.newEmail" placeholder="输入新的辅助邮箱" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" @click="startSecurityTask" :loading="processing">
            <el-icon><Lock /></el-icon>
            开始执行
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 执行结果 -->
    <el-card shadow="hover" class="mt-4" v-if="taskResults.length > 0">
      <template #header>
        <span class="card-header">执行结果</span>
      </template>
      <el-table :data="taskResults" stripe>
        <el-table-column prop="email" label="账号" width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="说明" />
        <el-table-column label="结果数据" width="200">
          <template #default="{ row }">
            <el-button v-if="row.new_secret" size="small" @click="showSecret(row)">
              查看新密钥
            </el-button>
            <el-button v-if="row.backup_codes?.length" size="small" @click="showBackupCodes(row)">
              查看备份码
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 密钥查看对话框 -->
    <el-dialog v-model="secretDialogVisible" title="新的 2FA 密钥" width="400">
      <div class="secret-display">
        <el-input :model-value="currentSecret" readonly>
          <template #append>
            <el-button @click="copySecret">复制</el-button>
          </template>
        </el-input>
      </div>
    </el-dialog>

    <!-- 备份码查看对话框 -->
    <el-dialog v-model="codesDialogVisible" title="备份验证码" width="400">
      <div class="codes-list">
        <el-tag v-for="code in currentBackupCodes" :key="code" class="code-item">
          {{ code }}
        </el-tag>
      </div>
      <template #footer>
        <el-button @click="copyAllCodes">复制全部</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock } from '@element-plus/icons-vue'
import { googleAccountsApi, googleSecurityApi, googleCeleryTasksApi } from '@/api/google'
import type { GoogleAccount } from '@/types'

const processing = ref(false)
const availableAccounts = ref<GoogleAccount[]>([])
const taskResults = ref<any[]>([])
const pollingTimer = ref<number | null>(null)

const secretDialogVisible = ref(false)
const codesDialogVisible = ref(false)
const currentSecret = ref('')
const currentBackupCodes = ref<string[]>([])

const securityForm = reactive({
  accounts: [] as number[],
  action: 'change_2fa' as string,
  newEmail: '',
})

onMounted(async () => {
  await loadAccounts()
})

onBeforeUnmount(() => {
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
    pollingTimer.value = null
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

async function startSecurityTask() {
  if (securityForm.accounts.length === 0) {
    ElMessage.warning('请选择至少一个账号')
    return
  }

  if ((securityForm.action === 'change_email' || securityForm.action === 'one_click') && !securityForm.newEmail) {
    ElMessage.warning('请输入新的辅助邮箱')
    return
  }

  processing.value = true
  taskResults.value = []

  try {
    const params = {
      account_ids: securityForm.accounts,
      new_email: securityForm.newEmail,
    }

    let response
    switch (securityForm.action) {
      case 'change_2fa':
        response = await googleSecurityApi.change2fa(params)
        break
      case 'change_email':
        response = await googleSecurityApi.changeRecoveryEmail(params)
        break
      case 'get_backup_codes':
        response = await googleSecurityApi.getBackupCodes(params)
        break
      case 'one_click':
        response = await googleSecurityApi.oneClickUpdate(params)
        break
    }

    if (!response || !response.task_id) {
      throw new Error(response?.error || response?.message || '任务提交失败')
    }

    ElMessage.success(`任务已提交，任务ID: ${response.task_id}`)

    // 轮询任务状态
    pollTaskStatus(String(response.task_id))
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '任务提交失败')
    processing.value = false
  } finally {
    // processing 在轮询结束时置回 false
  }
}

async function pollTaskStatus(taskId: string) {
  if (pollingTimer.value) {
    window.clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }

  const pollOnce = async () => {
    const status = await googleCeleryTasksApi.getTask(taskId)

    if (status.state === 'PROGRESS') {
      // 可选：这里可以展示进度（当前代码先不改 UI，只保留真实轮询）
      return
    }

    if (status.state === 'SUCCESS') {
      const res = status.result || {}
      const rawResults: any[] = Array.isArray(res.results) ? res.results : []

      // 兼容 one_click 返回 data 字段：把常用字段拍平到表格可展示的 new_secret / backup_codes
      taskResults.value = rawResults.map((r) => {
        const data = r.data || {}
        return {
          ...r,
          new_secret: r.new_secret || data.new_2fa_secret || null,
          backup_codes: r.backup_codes || data.backup_codes || [],
        }
      })

      if (pollingTimer.value) {
        window.clearInterval(pollingTimer.value)
        pollingTimer.value = null
      }
      processing.value = false
      return
    }

    if (status.state === 'FAILURE') {
      if (pollingTimer.value) {
        window.clearInterval(pollingTimer.value)
        pollingTimer.value = null
      }
      processing.value = false
      ElMessage.error(status.error || '任务执行失败')
    }
  }

  // 立即拉一次，避免首屏空等
  try {
    await pollOnce()
  } catch (e: any) {
    processing.value = false
    ElMessage.error(e?.message || '任务状态查询失败')
    return
  }

  pollingTimer.value = window.setInterval(async () => {
    try {
      await pollOnce()
    } catch (e: any) {
      // 网络抖动：继续轮询
      console.error('pollTaskStatus failed:', e)
    }
  }, 2000)
}

function showSecret(row: any) {
  currentSecret.value = row.new_secret
  secretDialogVisible.value = true
}

function showBackupCodes(row: any) {
  currentBackupCodes.value = row.backup_codes
  codesDialogVisible.value = true
}

function copySecret() {
  navigator.clipboard.writeText(currentSecret.value)
  ElMessage.success('已复制到剪贴板')
}

function copyAllCodes() {
  navigator.clipboard.writeText(currentBackupCodes.value.join('\n'))
  ElMessage.success('已复制到剪贴板')
}
</script>

<style scoped lang="scss">
.security-module {
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

  .secret-display {
    padding: 16px 0;
  }

  .codes-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 16px 0;

    .code-item {
      font-family: monospace;
      font-size: 14px;
    }
  }
}
</style>
