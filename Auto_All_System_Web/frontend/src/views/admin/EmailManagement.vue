<template>
  <div class="email-management">
    <div class="page-header">
      <h1>📧 域名邮箱管理</h1>
      <el-button type="primary" @click="openAddDialog">
        <el-icon><Plus /></el-icon>
        添加配置
      </el-button>
    </div>

    <el-card shadow="hover">
      <el-table :data="configs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="配置名称" width="150">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <el-tag v-if="row.is_default" type="success" size="small" class="ml-2">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="api_base" label="API 地址" min-width="250">
          <template #default="{ row }">
            <code>{{ row.api_base }}</code>
          </template>
        </el-table-column>
        <el-table-column label="API Token" width="160">
          <template #default="{ row }">
            <code>{{ row.masked_token }}</code>
          </template>
        </el-table-column>
        <el-table-column label="可用域名" width="200">
          <template #default="{ row }">
            <div class="domains-cell">
              <el-tag 
                v-for="(domain, idx) in row.domains?.slice(0, 2)" 
                :key="idx" 
                size="small" 
                class="mr-1"
              >
                {{ domain }}
              </el-tag>
              <el-tag v-if="row.domains?.length > 2" type="info" size="small">
                +{{ row.domains.length - 2 }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="toggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="editConfig(row)">编辑</el-button>
            <el-button text type="success" @click="testConnection(row)" :loading="row.testing">测试连接</el-button>
            <el-button text type="warning" @click="testCreateEmail(row)">测试创建邮箱</el-button>
            <el-button v-if="!row.is_default" text type="info" @click="setDefault(row)">设为默认</el-button>
            <el-button text type="danger" @click="deleteConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog 
      v-model="showDialog" 
      :title="editingConfig ? '编辑配置' : '添加配置'"
      width="600px"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="formData.name" placeholder="给配置起个名字" />
        </el-form-item>
        <el-form-item label="API 地址" prop="api_base">
          <el-input v-model="formData.api_base" placeholder="https://mail.example.com/api/public" />
        </el-form-item>
        <el-form-item label="API Token" prop="api_token">
          <el-input 
            v-model="formData.api_token" 
            placeholder="API Token (通过 genToken 接口获取)" 
            show-password
          />
        </el-form-item>
        <el-form-item label="可用域名" prop="domains">
          <div class="domains-input">
            <el-tag
              v-for="domain in formData.domains"
              :key="domain"
              closable
              @close="removeDomain(domain)"
              class="mr-1 mb-1"
            >
              {{ domain }}
            </el-tag>
            <el-input
              v-if="domainInputVisible"
              ref="domainInputRef"
              v-model="domainInputValue"
              size="small"
              style="width: 200px"
              placeholder="输入域名或粘贴JSON数组"
              @keyup.enter="addDomain"
              @blur="addDomain"
              @paste="handlePasteDomains"
            />
            <el-button v-else size="small" @click="showDomainInput">
              + 添加域名
            </el-button>
            <el-button size="small" type="info" @click="clearDomains" v-if="formData.domains.length">
              清空
            </el-button>
          </div>
          <div class="domains-tip">支持粘贴 JSON 数组格式，如 ["a.com", "b.com"]</div>
        </el-form-item>
        <el-form-item label="默认角色">
          <el-input v-model="formData.default_role" placeholder="user" />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="formData.is_default" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 测试创建邮箱对话框 -->
    <el-dialog v-model="showTestDialog" title="测试创建邮箱" width="500px">
      <div v-if="testResult" class="test-result">
        <el-result 
          :icon="testResult.success ? 'success' : 'error'" 
          :title="testResult.success ? '创建成功' : '创建失败'"
          :sub-title="testResult.message"
        >
          <template #extra v-if="testResult.data">
            <div class="result-info">
              <div class="info-item">
                <span class="label">邮箱地址:</span>
                <code>{{ testResult.data.email }}</code>
                <el-button text type="primary" size="small" @click="copyText(testResult.data.email)">复制</el-button>
              </div>
              <div class="info-item">
                <span class="label">密码:</span>
                <code>{{ testResult.data.password }}</code>
                <el-button text type="primary" size="small" @click="copyText(testResult.data.password)">复制</el-button>
              </div>
            </div>
          </template>
        </el-result>
      </div>
      <div v-else class="test-loading">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p>正在创建测试邮箱...</p>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Loading } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import {
  getCloudMailConfigs,
  getCloudMailConfig,
  createCloudMailConfig,
  updateCloudMailConfig,
  deleteCloudMailConfig,
  testCloudMailConnection,
  testCloudMailEmail,
  setDefaultCloudMailConfig,
  type CloudMailConfig
} from '@/api/email'

const loading = ref(false)
const saving = ref(false)
const configs = ref<(CloudMailConfig & { testing?: boolean })[]>([])
const showDialog = ref(false)
const showTestDialog = ref(false)
const editingConfig = ref<CloudMailConfig | null>(null)
const formRef = ref<FormInstance>()

// 域名输入相关
const domainInputVisible = ref(false)
const domainInputValue = ref('')
const domainInputRef = ref<HTMLInputElement>()

// 测试结果
const testResult = ref<{ success: boolean; message: string; data?: { email: string; password: string } } | null>(null)

const formData = reactive({
  name: '',
  api_base: '',
  api_token: '',
  domains: [] as string[],
  default_role: 'user',
  is_default: false,
  is_active: true
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  api_base: [
    { required: true, message: '请输入 API 地址', trigger: 'blur' },
    { type: 'url', message: '请输入正确的 URL 格式', trigger: 'blur' }
  ],
  api_token: [{ required: true, message: '请输入 API Token', trigger: 'blur' }]
}

const fetchConfigs = async () => {
  loading.value = true
  try {
    const res = await getCloudMailConfigs()
    // axios 拦截器已解包，res 直接是响应体
    configs.value = Array.isArray(res) ? res : res.results || []
  } catch (error) {
    ElMessage.error('获取配置列表失败')
  } finally {
    loading.value = false
  }
}

const openAddDialog = () => {
  editingConfig.value = null
  Object.assign(formData, {
    name: '',
    api_base: '',
    api_token: '',
    domains: [],
    default_role: 'user',
    is_default: false,
    is_active: true
  })
  showDialog.value = true
}

const editConfig = async (row: CloudMailConfig) => {
  editingConfig.value = row
  try {
    // 获取完整信息（包含未遮掩的 token）
    const res = await getCloudMailConfig(row.id)
    Object.assign(formData, {
      name: res.name,
      api_base: res.api_base,
      api_token: res.api_token || '',
      domains: res.domains || [],
      default_role: res.default_role || 'user',
      is_default: res.is_default,
      is_active: res.is_active
    })
    showDialog.value = true
  } catch {
    ElMessage.error('获取配置详情失败')
  }
}

const handleSave = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true
    try {
      if (editingConfig.value) {
        await updateCloudMailConfig(editingConfig.value.id, formData)
        ElMessage.success('更新成功')
      } else {
        await createCloudMailConfig(formData)
        ElMessage.success('添加成功')
      }
      showDialog.value = false
      fetchConfigs()
    } catch {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

const testConnection = async (row: CloudMailConfig & { testing?: boolean }) => {
  row.testing = true
  try {
    const res = await testCloudMailConnection(row.id)
    if (res.success) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  } catch {
    ElMessage.error('测试连接失败')
  } finally {
    row.testing = false
  }
}

const testCreateEmail = async (row: CloudMailConfig) => {
  showTestDialog.value = true
  testResult.value = null
  
  try {
    const res = await testCloudMailEmail(row.id, 'test@example.com')
    testResult.value = res
  } catch (err: any) {
    testResult.value = {
      success: false,
      message: err.response?.data?.message || err.message || '请求失败'
    }
  }
}

const toggleActive = async (row: CloudMailConfig) => {
  try {
    await updateCloudMailConfig(row.id, { is_active: row.is_active })
    ElMessage.success(`已${row.is_active ? '启用' : '禁用'}配置`)
  } catch {
    ElMessage.error('操作失败')
    row.is_active = !row.is_active
  }
}

const setDefault = async (row: CloudMailConfig) => {
  try {
    await setDefaultCloudMailConfig(row.id)
    ElMessage.success(`已将 ${row.name} 设置为默认配置`)
    fetchConfigs()
  } catch {
    ElMessage.error('设置失败')
  }
}

const deleteConfig = async (row: CloudMailConfig) => {
  try {
    await ElMessageBox.confirm(`确定删除配置 "${row.name}" 吗？`, '提示', {
      type: 'warning'
    })
    await deleteCloudMailConfig(row.id)
    ElMessage.success('删除成功')
    fetchConfigs()
  } catch {
    // 用户取消
  }
}

// 域名标签输入
const showDomainInput = () => {
  domainInputVisible.value = true
  nextTick(() => {
    domainInputRef.value?.focus()
  })
}

const normalizeDomain = (value: string) => {
  let raw = (value || '').trim().toLowerCase()
  if (!raw) return ''

  if (raw.includes('@')) {
    raw = raw.split('@')[1].trim()
  }
  if (raw.includes('://')) {
    try {
      raw = new URL(raw).host
    } catch {
      raw = raw.split('://')[1]
    }
  }
  raw = raw.split('/')[0].split('?')[0].split('#')[0].trim()
  if (raw.includes(':')) raw = raw.split(':')[0].trim()

  // 仅做基础校验，避免把 url/path 存进去导致创建邮箱失败
  if (!/^[a-z0-9.-]+$/.test(raw)) return ''
  if (!raw.includes('.')) return ''

  return raw
}

const addDomain = () => {
  const value = domainInputValue.value.trim()
  if (value) {
    // 尝试解析为 JSON 数组
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) {
        parsed.forEach((d: string) => {
          const domain = normalizeDomain(String(d || ''))
          if (domain && !formData.domains.includes(domain)) {
            formData.domains.push(domain)
          }
        })
      } else {
        const domain = normalizeDomain(value)
        if (domain && !formData.domains.includes(domain)) {
          formData.domains.push(domain)
        }
      }
    } catch {
      const domain = normalizeDomain(value)
      if (domain && !formData.domains.includes(domain)) {
        formData.domains.push(domain)
      }
    }
  }
  domainInputVisible.value = false
  domainInputValue.value = ''
}

const handlePasteDomains = (e: ClipboardEvent) => {
  const text = e.clipboardData?.getData('text')?.trim()
  if (!text) return
  
  // 尝试解析为 JSON 数组
  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed)) {
      e.preventDefault()
      parsed.forEach((d: string) => {
        const domain = normalizeDomain(String(d || ''))
        if (domain && !formData.domains.includes(domain)) {
          formData.domains.push(domain)
        }
      })
      domainInputVisible.value = false
      domainInputValue.value = ''
      ElMessage.success(`已添加 ${parsed.length} 个域名`)
    }
  } catch {
    // 不是 JSON，正常粘贴
  }
}

const clearDomains = () => {
  formData.domains = []
}

const removeDomain = (domain: string) => {
  const index = formData.domains.indexOf(domain)
  if (index > -1) {
    formData.domains.splice(index, 1)
  }
}

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style scoped lang="scss">
.email-management {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    h1 {
      margin: 0;
    }
  }

  code {
    background: #f5f7fa;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    color: #409eff;
  }

  .domains-cell {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .domains-input {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
  }

  .domains-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }

  .ml-2 {
    margin-left: 8px;
  }

  .mr-1 {
    margin-right: 4px;
  }

  .mb-1 {
    margin-bottom: 4px;
  }
}

.test-result {
  .result-info {
    text-align: left;
    background: #f5f7fa;
    padding: 16px;
    border-radius: 8px;
    
    .info-item {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .label {
        font-weight: 500;
        min-width: 70px;
      }
      
      code {
        background: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
      }
    }
  }
}

.test-loading {
  text-align: center;
  padding: 40px;
  
  p {
    margin-top: 16px;
    color: #909399;
  }
}
</style>
