<template>
  <div class="accounts">
    <div class="header">
      <div>
        <div class="title">账号列表</div>
        <div class="sub">母号可展开查看子账号；邮箱由域名邮箱系统随机创建（来源：admin/email）</div>
      </div>

      <div class="actions">
        <el-button @click="refresh" :loading="loading">刷新</el-button>
        <el-button type="primary" @click="openCreateMother">生成母号</el-button>

        <span class="selected" :title="selectedMother?.email || ''">
          已选：<span class="mono">{{ selectedMother?.email || '-' }}</span>
        </span>

        <el-button type="success" :disabled="!selectedMother" @click="runSelfRegister">自动开通</el-button>
        <el-button type="warning" :disabled="!selectedMother" @click="runAutoInvite">自动邀请</el-button>
        <el-button type="info" :disabled="!selectedMother" @click="runSub2apiSink">自动入池</el-button>
      </div>
    </div>

    <el-card shadow="never">
      <el-table
        :data="mothers"
        row-key="id"
        v-loading="loading"
        highlight-current-row
        @current-change="onCurrentChange"
        style="width: 100%;"
      >
        <el-table-column type="expand">
          <template #default="props">
            <div class="expand">
              <div class="expand-title">子账号（{{ props.row.children?.length || 0 }}）</div>
              <el-table :data="props.row.children || []" row-key="id" size="small" style="width: 100%;">
                <el-table-column prop="email" label="邮箱" min-width="220" />
                <el-table-column label="账号密码" min-width="220">
                  <template #default="scope">
                    <div class="cell-actions">
                      <span class="mono">{{ scope.row.account_password || '-' }}</span>
                      <el-button v-if="scope.row.account_password" text type="primary" @click="copyAccountPassword(scope.row)">
                        复制
                      </el-button>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="邮箱密码" min-width="220">
                  <template #default="scope">
                    <div class="cell-actions">
                      <span class="mono">{{ scope.row.email_password }}</span>
                      <el-button text type="primary" @click="copyEmailPassword(scope.row)">复制</el-button>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="note" label="备注" min-width="160" />
                <el-table-column label="创建时间" min-width="170">
                  <template #default="scope">
                    <span class="muted">{{ scope.row.created_at || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="200" fixed="right">
                  <template #default="scope">
                    <el-button text @click="launchGeekez(scope.row.id)">打开Geekez</el-button>
                    <el-button text type="primary" @click="copyFull(scope.row)">复制账号</el-button>
                    <el-button text type="danger" @click="removeAccount(scope.row.id)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="email" label="母号邮箱" min-width="220" />

        <el-table-column label="账号密码" min-width="220">
          <template #default="scope">
            <div class="cell-actions">
              <span class="mono">{{ scope.row.account_password || '-' }}</span>
              <el-button v-if="scope.row.account_password" text type="primary" @click="copyAccountPassword(scope.row)">
                复制
              </el-button>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="邮箱密码" min-width="220">
          <template #default="scope">
            <div class="cell-actions">
              <span class="mono">{{ scope.row.email_password || '-' }}</span>
              <el-button v-if="scope.row.email_password" text type="primary" @click="copyEmailPassword(scope.row)">
                复制
              </el-button>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="座位" width="140">
          <template #default="scope">
            <span class="mono">{{ scope.row.seat_used || 0 }}/{{ scope.row.seat_total || 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="note" label="备注" min-width="160" />

        <el-table-column label="创建时间" min-width="170">
          <template #default="scope">
            <span class="muted">{{ scope.row.created_at || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="360" fixed="right">
          <template #default="scope">
            <el-button text type="primary" @click="openCreateChild(scope.row)">生成子号</el-button>
            <el-button text @click="editSeat(scope.row)">改座位</el-button>
            <el-button text @click="viewTasks(scope.row)">任务日志</el-button>
            <el-button text @click="launchGeekez(scope.row.id)">打开Geekez</el-button>
            <el-button text type="danger" @click="removeAccount(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="motherDialogVisible" title="生成母号" width="520px">
      <el-form :model="motherForm" label-width="90px">
        <el-form-item label="邮箱配置">
          <el-select
            v-model="motherForm.cloudmail_config_id"
            filterable
            placeholder="请选择 admin/email 配置"
            style="width: 100%;"
          >
            <el-option
              v-for="cfg in cloudMailConfigs"
              :key="cfg.id"
              :label="`${cfg.name}${cfg.is_default ? ' (默认)' : ''}  (${cfg.domains_count || cfg.domains?.length || 0} domains)`"
              :value="cfg.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="域名">
          <el-select v-model="motherForm.domain" filterable clearable placeholder="留空=随机" style="width: 100%;">
            <el-option v-for="d in motherDomains" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="座位数">
          <el-input-number v-model="motherForm.seat_total" :min="0" :max="500" />
        </el-form-item>

        <el-form-item label="生成数量">
          <el-input-number v-model="motherForm.count" :min="1" :max="200" />
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="motherForm.note" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="motherDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createMother">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="childDialogVisible" title="生成子账号" width="520px">
      <el-form :model="childForm" label-width="90px">
        <el-form-item label="母号">
          <el-input :model-value="activeMother?.email || ''" disabled />
        </el-form-item>
        <el-form-item label="域名">
          <el-select v-model="childForm.domain" filterable clearable placeholder="留空=随机" style="width: 100%;">
            <el-option v-for="d in childDomains" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>

        <el-form-item label="生成数量">
          <el-input-number v-model="childForm.count" :min="1" :max="500" />
        </el-form-item>

        <el-form-item label="备注">
          <el-input v-model="childForm.note" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="childDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createChild">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="tasksDrawerVisible" title="任务日志" size="600px">
      <div v-if="tasksDrawerAccount">
        <div class="drawer-account-info">
          <span class="mono">{{ tasksDrawerAccount.email }}</span>
        </div>
        <el-table :data="accountTasks" v-loading="tasksLoading" size="small" style="width: 100%;">
          <el-table-column prop="type" label="类型" width="120">
            <template #default="scope">
              <el-tag size="small" :type="getTaskTypeTag(scope.row.type)">{{ getTaskTypeName(scope.row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag size="small" :type="getStatusTag(scope.row.status)">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="160">
            <template #default="scope">
              <span class="muted">{{ scope.row.created_at || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="错误" min-width="200">
            <template #default="scope">
              <span class="muted" style="color: #ef4444;">{{ scope.row.error || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="产物" width="80">
            <template #default="scope">
              <el-button link type="primary" size="small" @click="viewTaskArtifacts(scope.row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!tasksLoading && accountTasks.length === 0" description="暂无任务记录" />
      </div>
    </el-drawer>

    <el-dialog v-model="artifactsDialogVisible" title="任务产物" width="520px">
      <el-table :data="currentTaskArtifacts" v-loading="artifactsLoading" size="small" style="width: 100%;">
        <el-table-column prop="name" label="文件" min-width="200" />
        <el-table-column label="下载" width="100">
          <template #default="scope">
            <el-link :href="scope.row.download_url" target="_blank" type="primary">下载</el-link>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!artifactsLoading && currentTaskArtifacts.length === 0" description="暂无产物" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCloudMailConfigs, type CloudMailConfig } from '@/api/email'
import type { GptBusinessAccount, GptBusinessAccountsResponse } from '@/api/gpt_business'
import { gptBusinessApi } from '@/api/gpt_business'

type MotherRow = GptBusinessAccountsResponse['mothers'][number]

const loading = ref(false)
const creating = ref(false)

const mothers = ref<MotherRow[]>([])
const cloudMailConfigs = ref<CloudMailConfig[]>([])

const selectedMotherId = ref('')

const selectedMother = computed(() => {
  return mothers.value.find(m => m.id === selectedMotherId.value) || null
})

const motherDialogVisible = ref(false)
const childDialogVisible = ref(false)

const activeMother = ref<MotherRow | null>(null)

const motherForm = reactive({
  cloudmail_config_id: 0,
  domain: '',
  seat_total: 4,
  count: 1,
  note: ''
})

const childForm = reactive({
  domain: '',
  count: 1,
  note: ''
})

const selectedMotherConfig = computed(() => {
  if (!motherForm.cloudmail_config_id) return null
  return cloudMailConfigs.value.find(c => c.id === motherForm.cloudmail_config_id) || null
})

const motherDomains = computed(() => {
  return selectedMotherConfig.value?.domains || []
})

const childDomains = computed(() => {
  const configId = activeMother.value?.cloudmail_config_id
  if (!configId) return []
  const cfg = cloudMailConfigs.value.find(c => c.id === configId)
  return cfg?.domains || []
})

const fetchCloudMailConfigs = async () => {
  const res = await getCloudMailConfigs()
  const list = Array.isArray(res) ? res : res.results || []
  cloudMailConfigs.value = list.filter(c => c.is_active)
}

const refresh = async () => {
  loading.value = true
  try {
    const [accounts, _configs] = await Promise.all([gptBusinessApi.listAccounts(), fetchCloudMailConfigs()])
    mothers.value = accounts.mothers || []

    // 重新对齐当前选中
    if (selectedMotherId.value) {
      const exists = mothers.value.some(m => m.id === selectedMotherId.value)
      if (!exists) selectedMotherId.value = ''
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const onCurrentChange = (row: MotherRow | undefined) => {
  selectedMotherId.value = row?.id || ''
}

const openCreateMother = () => {
  const defaultCfg = cloudMailConfigs.value.find(c => c.is_default) || cloudMailConfigs.value[0]
  motherForm.cloudmail_config_id = defaultCfg?.id || 0
  motherForm.domain = ''
  motherForm.seat_total = 4
  motherForm.count = 1
  motherForm.note = ''
  motherDialogVisible.value = true
}

const createMother = async () => {
  if (!motherForm.cloudmail_config_id) {
    ElMessage.warning('请先选择邮箱配置')
    return
  }
  creating.value = true
  try {
    const res = await gptBusinessApi.createMotherAccounts({
      cloudmail_config_id: motherForm.cloudmail_config_id,
      domain: motherForm.domain || undefined,
      seat_total: motherForm.seat_total,
      count: motherForm.count,
      note: motherForm.note || undefined
    })
    ElMessage.success(`已创建母号 x${res.created?.length || 0}`)
    motherDialogVisible.value = false
    await refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const openCreateChild = (mother: MotherRow) => {
  activeMother.value = mother
  childForm.domain = ''
  childForm.count = 1
  childForm.note = ''
  childDialogVisible.value = true
}

const createChild = async () => {
  if (!activeMother.value) return
  creating.value = true
  try {
    const res = await gptBusinessApi.createChildAccounts({
      parent_id: activeMother.value.id,
      cloudmail_config_id: activeMother.value.cloudmail_config_id || undefined,
      domain: childForm.domain || undefined,
      count: childForm.count,
      note: childForm.note || undefined
    })
    ElMessage.success(`已创建子号 x${res.created?.length || 0}`)
    childDialogVisible.value = false
    await refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败（浏览器不支持剪贴板）')
  }
}

const copyFull = (acc: GptBusinessAccount) => {
  const lines = [
    acc.email,
    acc.account_password ? `account_password: ${acc.account_password}` : '',
    acc.email_password ? `email_password: ${acc.email_password}` : ''
  ].filter(Boolean)
  copyText(lines.join('\n'))
}

const copyAccountPassword = (acc: GptBusinessAccount) => {
  if (!acc.account_password) return
  copyText(acc.account_password)
}

const copyEmailPassword = (acc: GptBusinessAccount) => {
  if (!acc.email_password) return
  copyText(acc.email_password)
}

const editSeat = async (mother: MotherRow) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入母号座位数（seat_total）', '修改座位', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: String(mother.seat_total || 0),
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入非负整数'
    })

    const seatTotal = Number(value)
    await gptBusinessApi.updateAccount(mother.id, { seat_total: seatTotal })
    ElMessage.success('已更新')
    await refresh()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '更新失败')
  }
}

const removeAccount = async (accountId: string) => {
  try {
    await ElMessageBox.confirm('删除后不可恢复；删除母号会同时删除其子账号。确认删除？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await gptBusinessApi.deleteAccount(accountId)
    ElMessage.success('已删除')
    await refresh()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

const launchGeekez = async (accountId: string) => {
  try {
    const res = await gptBusinessApi.launchGeekez(accountId)
    if (res?.success) {
      ElMessage.success('已启动 Geekez 环境')
    } else {
      ElMessage.warning('启动失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const runSelfRegister = async () => {
  if (!selectedMother.value) {
    ElMessage.warning('请先选中一个母号')
    return
  }
  try {
    const res = await gptBusinessApi.selfRegister(selectedMother.value.id)
    ElMessage.success(res?.message || '已启动：自动开通')
    refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const runAutoInvite = async () => {
  if (!selectedMother.value) return
  try {
    const res = await gptBusinessApi.autoInvite(selectedMother.value.id)
    ElMessage.success(res?.message || '已启动：自动邀请')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const runSub2apiSink = async () => {
  if (!selectedMother.value) return
  try {
    const res = await gptBusinessApi.sub2apiSink(selectedMother.value.id)
    ElMessage.success(res?.message || '已启动：自动入池')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const tasksDrawerVisible = ref(false)
const tasksDrawerAccount = ref<MotherRow | null>(null)
type TaskRow = {
  id: string
  type?: string
  status?: string
  mother_id?: string
  created_at?: string
  error?: string
}

type TaskArtifact = { name: string; download_url: string }

const accountTasks = ref<TaskRow[]>([])
const tasksLoading = ref(false)

const artifactsDialogVisible = ref(false)
const artifactsLoading = ref(false)
const currentTaskArtifacts = ref<TaskArtifact[]>([])

const viewTasks = async (mother: MotherRow) => {
  tasksDrawerAccount.value = mother
  tasksDrawerVisible.value = true
  tasksLoading.value = true
  try {
    const res = await gptBusinessApi.listTasks()
    const allTasks: TaskRow[] = (res?.tasks || []) as TaskRow[]
    accountTasks.value = allTasks.filter(t => t.mother_id === mother.id)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取任务失败')
    accountTasks.value = []
  } finally {
    tasksLoading.value = false
  }
}

const viewTaskArtifacts = async (task: TaskRow) => {
  if (!task?.id) return
  artifactsDialogVisible.value = true
  artifactsLoading.value = true
  currentTaskArtifacts.value = []
  try {
    const artifacts = await gptBusinessApi.getTaskArtifacts(task.id)
    currentTaskArtifacts.value = artifacts || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取产物失败')
    currentTaskArtifacts.value = []
  } finally {
    artifactsLoading.value = false
  }
}

const getTaskTypeName = (type: string) => {
  const map: Record<string, string> = {
    self_register: '自动开通',
    auto_invite: '自动邀请',
    sub2api_sink: '自动入池'
  }
  return map[type] || type
}

const getTaskTypeTag = (type: string) => {
  const map: Record<string, string> = {
    self_register: 'success',
    auto_invite: 'warning',
    sub2api_sink: 'info'
  }
  return map[type] || ''
}

const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    running: 'primary',
    pending: 'info'
  }
  return map[status] || 'info'
}

onMounted(() => {
  refresh()
})
</script>

<style scoped lang="scss">
.accounts {
  .header {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 12px;

    .title {
      font-size: 16px;
      font-weight: 700;
      color: #111827;
    }

    .sub {
      margin-top: 4px;
      font-size: 12px;
      color: #6b7280;
    }

    .actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
  }

  .expand {
    padding: 8px 0;

    .expand-title {
      font-size: 13px;
      font-weight: 600;
      color: #374151;
      margin-bottom: 8px;
    }
  }

  .mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  }

  .muted {
    color: #6b7280;
  }

  .cell-actions {
    display: inline-flex;
    gap: 8px;
    align-items: center;
  }

  .selected {
    font-size: 12px;
    color: #374151;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .drawer-account-info {
    margin-bottom: 16px;
    padding: 12px;
    background: #f3f4f6;
    border-radius: 6px;
  }
}
</style>
