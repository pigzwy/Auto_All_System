<template>
  <div class="space-y-6 p-5">
    <!-- 页头 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 class="text-2xl font-bold tracking-tight text-foreground">Google 账号管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">管理所有 Google 账号信息</p>
      </div>
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <Button variant="secondary" type="button" @click="showImportDialog = true">
          <Icon><Upload /></Icon>
          <span class="ml-1.5">批量导入</span>
        </Button>
        <Button variant="success" type="button" @click="showAddDialog = true">
          <Icon><Plus /></Icon>
          <span class="ml-1.5">添加账号</span>
        </Button>
      </div>
    </div>

    <!-- 筛选和搜索 -->
    <Card class="shadow-sm">
      <CardContent class="p-5">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-12">
          <div class="md:col-span-3">
          <SelectNative
            v-model="statusFilter"
            placeholder="状态筛选"
            clearable
            @change="loadAccounts"
            class="w-full"
          >
            <SelectOption
              v-for="item in statusOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </SelectNative>
          </div>

          <div class="md:col-span-7">
          <TextInput
            v-model="searchQuery"
            placeholder="搜索邮箱或备注"
            clearable
            @input="loadAccounts"
            class="w-full"
          >
            <template #prefix>
              <Icon><Search /></Icon>
            </template>
          </TextInput>
          </div>

          <div class="md:col-span-2">
          <Button  variant="secondary" type="button" class="w-full" @click="loadAccounts">
            <Icon><Refresh /></Icon>
            <span class="ml-1.5">刷新</span>
          </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 数据表格 -->
    <Card class="shadow-sm">
      <CardHeader class="pb-3">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle class="text-base">账号列表</CardTitle>
          <div class="flex flex-wrap items-center gap-2">
            <Button
              v-if="selectedAccounts.length > 0"
              type="danger"
              size="small"
              @click="handleBulkDelete"
            >
              <Icon><Delete /></Icon>
              <span class="ml-1.5">批量删除 ({{ selectedAccounts.length }})</span>
            </Button>
            <Badge variant="secondary">共 {{ accounts.length }} 个账号</Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <DataTable
          :data="accounts"
          v-loading="loading"
          stripe
          class="w-full"
          @selection-change="handleSelectionChange"
        >
        <DataColumn type="selection" width="55" />
        <DataColumn prop="email" label="邮箱" min-width="200" />
        <DataColumn prop="browser_id" label="浏览器ID" width="150">
          <template #default="{ row }">
            <code
              v-if="row.browser_id"
              class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-primary"
            >
              {{ row.browser_id.substring(0, 8) }}...
            </code>
            <span v-else class="text-muted-foreground">-</span>
          </template>
        </DataColumn>
        <DataColumn prop="status" label="状态" width="150">
          <template #default="{ row }">
            <Tag :type="getStatusType(row.status)" size="small">
              {{ row.status_display }}
            </Tag>
          </template>
        </DataColumn>
        <DataColumn prop="last_checked_at" label="最后检测" width="180">
          <template #default="{ row }">
            {{ formatTime(row.last_checked_at) || '-' }}
          </template>
        </DataColumn>
        <DataColumn label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <Button link  variant="default" type="button" @click="editAccount(row)">
              <Icon><Edit /></Icon>
            </Button>
            <Button link  variant="destructive" type="button" @click="deleteAccount(row)">
              <Icon><Delete /></Icon>
            </Button>
          </template>
        </DataColumn>
        </DataTable>
      </CardContent>
    </Card>

    <!-- 添加账号对话框 -->
    <Modal
      v-model="showAddDialog"
      title="添加 Google 账号"
      width="600px"
    >
      <SimpleForm :model="newAccount" label-width="100px">
        <SimpleFormItem label="邮箱" required>
          <TextInput v-model="newAccount.email" type="email" placeholder="user@gmail.com" />
        </SimpleFormItem>

        <SimpleFormItem label="密码" required>
          <TextInput v-model="newAccount.password" type="password" show-password placeholder="账号密码" />
        </SimpleFormItem>

        <SimpleFormItem label="辅助邮箱">
          <TextInput v-model="newAccount.recovery_email" type="email" placeholder="recovery@gmail.com" />
        </SimpleFormItem>

        <SimpleFormItem label="2FA密钥">
          <TextInput v-model="newAccount.secret_key" placeholder="ABCD1234EFGH5678" />
        </SimpleFormItem>

        <SimpleFormItem label="浏览器ID">
          <TextInput v-model="newAccount.browser_id" placeholder="Bitbrowser 浏览器ID" />
        </SimpleFormItem>

        <SimpleFormItem label="备注">
          <TextInput v-model="newAccount.notes" type="textarea" :rows="3" placeholder="备注信息" />
        </SimpleFormItem>
      </SimpleForm>

      <template #footer>
        <Button @click="showAddDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="saveAccount">保存</Button>
      </template>
    </Modal>

    <!-- 批量导入对话框 -->
    <Modal
      v-model="showImportDialog"
      title="批量导入账号"
      width="800px"
    >
      <InfoAlert
        type="info"
        :closable="false"
        class="mb-4"
      >
        <template #title>
          <div>
            <strong>格式：</strong>email----password----recovery_email----secret_key<br />
            每行一个账号
          </div>
        </template>
      </InfoAlert>

      <TextInput
        v-model="importText"
        type="textarea"
        :rows="12"
        placeholder="例如：user@gmail.com----pass123----backup@gmail.com----ABCD1234EFGH5678"
      />

      <template #footer>
        <Button @click="showImportDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="importAccounts">导入</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Upload,
  Plus,
  Search,
  Refresh,
  Edit,
  Delete
} from '@/icons'
import { getGoogleAccounts, createGoogleAccount, deleteGoogleAccount, batchImportGoogleAccounts, batchDeleteAccounts } from '@/api/google_business'

interface Account {
  id: number
  email: string
  password: string
  recovery_email?: string
  secret_key?: string
  browser_id?: string
  notes?: string
  status: string
  status_display: string
  last_checked_at?: string
}

const accounts = ref<Account[]>([])
const loading = ref(false)
const statusFilter = ref('')
const searchQuery = ref('')

const showAddDialog = ref(false)
const showImportDialog = ref(false)
const importText = ref('')
const selectedAccounts = ref<Account[]>([])

const newAccount = ref({
  email: '',
  password: '',
  recovery_email: '',
  secret_key: '',
  browser_id: '',
  notes: ''
})

const statusOptions = [
  { label: '待检测资格', value: 'pending_check' },
  { label: '有资格待验证', value: 'link_ready' },
  { label: '已验证未绑卡', value: 'verified' },
  { label: '已订阅', value: 'subscribed' },
  { label: '无资格', value: 'ineligible' },
  { label: '错误', value: 'error' }
]

const loadAccounts = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (searchQuery.value) params.search = searchQuery.value

    const response = await getGoogleAccounts(params)
    accounts.value = (response as any) || []
  } catch (error: any) {
    console.error('加载账号失败:', error)
    ElMessage.error('加载账号失败')
  } finally {
    loading.value = false
  }
}

const saveAccount = async () => {
  if (!newAccount.value.email || !newAccount.value.password) {
    ElMessage.warning('邮箱和密码必填')
    return
  }

  try {
    await createGoogleAccount(newAccount.value)
    ElMessage.success('账号添加成功')
    showAddDialog.value = false
    newAccount.value = {
      email: '',
      password: '',
      recovery_email: '',
      secret_key: '',
      browser_id: '',
      notes: ''
    }
    loadAccounts()
  } catch (error: any) {
    console.error('保存账号失败:', error)
    ElMessage.error('保存账号失败')
  }
}

const importAccounts = async () => {
  const lines = importText.value.split('\n').filter(l => l.trim())
  if (lines.length === 0) {
    ElMessage.warning('请输入账号数据')
    return
  }

  const accountsData = lines.map(line => {
    const parts = line.split('----')
    return {
      email: parts[0]?.trim() || '',
      password: parts[1]?.trim() || '',
      recovery_email: parts[2]?.trim() || '',
      secret_key: parts[3]?.trim() || ''
    }
  })

  try {
    await batchImportGoogleAccounts(accountsData)
    ElMessage.success(`成功导入 ${accountsData.length} 个账号`)
    showImportDialog.value = false
    importText.value = ''
    loadAccounts()
  } catch (error: any) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败')
  }
}

const editAccount = (_account: Account) => {
  ElMessage.info('编辑功能开发中')
}

const deleteAccount = async (account: Account) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除账号 ${account.email} 吗？`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteGoogleAccount(account.id)
    ElMessage.success('删除成功')
    loadAccounts()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleSelectionChange = (selection: Account[]) => {
  selectedAccounts.value = selection
}

const handleBulkDelete = async () => {
  if (selectedAccounts.value.length === 0) {
    ElMessage.warning('请先选择要删除的账号')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedAccounts.value.length} 个账号吗？此操作不可恢复！`,
      '批量删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const ids = selectedAccounts.value.map(account => account.id)
    await batchDeleteAccounts({ ids })
    ElMessage.success(`成功删除 ${ids.length} 个账号`)
    selectedAccounts.value = []
    loadAccounts()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    'pending_check': 'info',
    'link_ready': 'primary',
    'verified': 'warning',
    'subscribed': 'success',
    'ineligible': 'danger',
    'error': 'danger'
  }
  return types[status] || 'info'
}

const formatTime = (datetime: string) => {
  if (!datetime) return ''
  return new Date(datetime).toLocaleString('zh-CN')
}

onMounted(() => {
  loadAccounts()
})
</script>
