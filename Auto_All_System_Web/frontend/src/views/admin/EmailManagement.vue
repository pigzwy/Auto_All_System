<template>
  <div class="space-y-6 p-5">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">域名邮箱管理</h1>
        <p class="mt-1 text-sm text-muted-foreground">管理云邮配置、域名池、默认配置与连通性测试。</p>
      </div>
      <Button  variant="default" type="button" @click="openAddDialog">
        <Icon><Plus /></Icon>
        添加配置
      </Button>
    </div>

    <Card class="shadow-sm">
      <CardContent class="p-6">
        <DataTable :data="configs" v-loading="loading" stripe class="w-full">
        <DataColumn prop="id" label="ID" width="60" />
        <DataColumn prop="name" label="配置名称" width="150">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <Tag v-if="row.is_default" type="success" size="small" class="ml-2">默认</Tag>
          </template>
        </DataColumn>
        <DataColumn prop="api_base" label="API 地址" min-width="250">
          <template #default="{ row }">
            <code class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-primary">{{ row.api_base }}</code>
          </template>
        </DataColumn>
        <DataColumn label="API Token" width="160">
          <template #default="{ row }">
            <code class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-primary">{{ row.masked_token }}</code>
          </template>
        </DataColumn>
        <DataColumn label="可用域名" width="200">
          <template #default="{ row }">
            <div class="flex flex-wrap items-center gap-1">
              <Tag 
                v-for="(domain, idx) in row.domains?.slice(0, 2)" 
                :key="idx" 
                size="small" 
              >
                {{ domain }}
              </Tag>
              <Tag v-if="row.domains?.length > 2" type="info" size="small">
                +{{ row.domains.length - 2 }}
              </Tag>
            </div>
          </template>
        </DataColumn>
        <DataColumn label="状态" width="80">
          <template #default="{ row }">
            <Toggle v-model="row.is_active" @change="toggleActive(row)" />
          </template>
        </DataColumn>
        <DataColumn label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <Button text  variant="default" type="button" @click="editConfig(row)">编辑</Button>
            <Button text  variant="default" type="button" @click="testConnection(row)" :loading="row.testing">测试连接</Button>
            <Button text  variant="secondary" type="button" @click="testCreateEmail(row)">测试创建邮箱</Button>
            <Button v-if="!row.is_default" text  variant="secondary" type="button" @click="setDefault(row)">设为默认</Button>
            <Button text  variant="destructive" type="button" @click="deleteConfig(row)">删除</Button>
          </template>
        </DataColumn>
      </DataTable>
      </CardContent>
    </Card>

    <!-- 添加/编辑对话框 -->
    <Modal 
      v-model="showDialog" 
      :title="editingConfig ? '编辑配置' : '添加配置'"
      width="600px"
    >
      <SimpleForm :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <SimpleFormItem label="配置名称" prop="name">
          <TextInput v-model="formData.name" placeholder="给配置起个名字" />
        </SimpleFormItem>
        <SimpleFormItem label="API 地址" prop="api_base">
          <TextInput v-model="formData.api_base" placeholder="https://mail.example.com/api/public" />
        </SimpleFormItem>
        <SimpleFormItem label="API Token" prop="api_token">
          <TextInput 
            v-model="formData.api_token" 
            placeholder="API Token (通过 genToken 接口获取)" 
            show-password
          />
        </SimpleFormItem>
        <SimpleFormItem label="可用域名" prop="domains">
          <div class="flex flex-wrap items-center gap-2">
            <Tag
              v-for="domain in formData.domains"
              :key="domain"
              closable
              @close="removeDomain(domain)"
            >
              {{ domain }}
            </Tag>
            <TextInput
              v-if="domainInputVisible"
              ref="domainInputRef"
              v-model="domainInputValue"
              size="small"
              class="w-[200px]"
              placeholder="输入域名或粘贴JSON数组"
              @keyup.enter="addDomain"
              @blur="addDomain"
              @paste="handlePasteDomains"
            />
            <Button v-else size="small" @click="showDomainInput">
              + 添加域名
            </Button>
            <Button size="small"  variant="secondary" type="button" @click="clearDomains" v-if="formData.domains.length">
              清空
            </Button>
          </div>
          <div class="mt-2 text-xs text-muted-foreground">支持粘贴 JSON 数组格式，如 ["a.com", "b.com"]</div>
        </SimpleFormItem>
        <SimpleFormItem label="默认角色">
          <TextInput v-model="formData.default_role" placeholder="user" />
        </SimpleFormItem>
        <SimpleFormItem label="设为默认">
          <Toggle v-model="formData.is_default" />
        </SimpleFormItem>
        <SimpleFormItem label="启用">
          <Toggle v-model="formData.is_active" />
        </SimpleFormItem>
      </SimpleForm>
      <template #footer>
        <Button @click="showDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="handleSave" :loading="saving">保存</Button>
      </template>
    </Modal>

    <!-- 测试创建邮箱对话框 -->
    <Modal v-model="showTestDialog" title="测试创建邮箱" width="500px">
      <div v-if="testResult">
        <Result 
          :icon="testResult.success ? 'success' : 'error'" 
          :title="testResult.success ? '创建成功' : '创建失败'"
          :sub-title="testResult.message"
        >
          <template #extra v-if="testResult.data">
            <div class="mt-4 rounded-lg border border-border bg-muted/20 p-4 text-left">
              <div class="flex flex-wrap items-center gap-2">
                <span class="w-20 text-xs font-medium text-muted-foreground">邮箱地址:</span>
                <code class="rounded bg-background px-2 py-1 font-mono text-xs text-foreground">{{ testResult.data.email }}</code>
                <Button text  variant="default" type="button" size="small" @click="copyText(testResult.data.email)">复制</Button>
              </div>
              <div class="mt-2 flex flex-wrap items-center gap-2">
                <span class="w-20 text-xs font-medium text-muted-foreground">密码:</span>
                <code class="rounded bg-background px-2 py-1 font-mono text-xs text-foreground">{{ testResult.data.password }}</code>
                <Button text  variant="default" type="button" size="small" @click="copyText(testResult.data.password)">复制</Button>
              </div>
            </div>
          </template>
        </Result>
      </div>
      <div v-else class="py-10 text-center">
        <Icon class="is-loading" :size="48"><Loading /></Icon>
        <p class="mt-4 text-sm text-muted-foreground">正在创建测试邮箱...</p>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Plus, Loading } from '@/icons'
import type { ElFormRules } from '@/components/app/symbols'
import { Card, CardContent } from '@/components/ui/card'
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
type ElFormExpose = {
  validate: (cb?: (valid: boolean) => void | Promise<void>) => Promise<boolean>
  resetFields?: () => void
}

const formRef = ref<ElFormExpose | null>(null)

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

const formRules: ElFormRules = {
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
