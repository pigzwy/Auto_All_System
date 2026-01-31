<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm">
      <CardContent class="px-4 py-3">
        <PageHeader @back="$router.push('/admin/google-business')" content="卡信息管理" />
      </CardContent>
    </Card>

    <!--搜索和操作 -->
    <Card class="shadow-sm">
      <CardContent class="space-y-4 p-6">
        <SimpleForm :inline="true" :model="searchForm">
        <SimpleFormItem label="搜索">
          <TextInput
            v-model="searchForm.search"
            placeholder="搜索卡号"
            clearable
            @keyup.enter="handleSearch"
          />
        </SimpleFormItem>

        <SimpleFormItem label="状态">
          <SelectNative v-model="searchForm.is_active" placeholder="全部" clearable @change="handleSearch">
            <SelectOption label="全部" :value="undefined" />
            <SelectOption label="可用" :value="true" />
            <SelectOption label="禁用" :value="false" />
          </SelectNative>
        </SimpleFormItem>

        <SimpleFormItem>
          <Button  variant="default" type="button" @click="handleSearch">
            <Icon><Search /></Icon>
            搜索
          </Button>
          <Button @click="handleReset">
            <Icon><RefreshLeft /></Icon>
            重置
          </Button>
        </SimpleFormItem>
        </SimpleForm>

      <Divider />

      <div class="flex flex-wrap gap-2">
        <Button  variant="default" type="button" @click="showAddDialog">
          <Icon><Plus /></Icon>
          添加卡片
        </Button>
        <Button  variant="default" type="button" @click="showBatchImportDialog">
          <Icon><Upload /></Icon>
          批量导入
        </Button>
        <Button
           variant="destructive" type="button"
          :disabled="selectedIds.length === 0"
          @click="handleBatchDelete"
        >
          <Icon><Delete /></Icon>
          批量删除 ({{ selectedIds.length }})
        </Button>
      </div>
      </CardContent>
    </Card>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6 text-center">
          <div class="text-3xl font-bold leading-none text-foreground">{{ cardStats.total || 0 }}</div>
          <div class="mt-2 text-sm text-muted-foreground">总卡片数</div>
        </CardContent>
      </Card>
      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6 text-center">
          <div class="text-3xl font-bold leading-none text-emerald-600">{{ cardStats.active || 0 }}</div>
          <div class="mt-2 text-sm text-muted-foreground">可用卡片</div>
        </CardContent>
      </Card>
      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6 text-center">
          <div class="text-3xl font-bold leading-none text-rose-600">{{ cardStats.inactive || 0 }}</div>
          <div class="mt-2 text-sm text-muted-foreground">禁用卡片</div>
        </CardContent>
      </Card>
      <Card class="shadow-sm transition-shadow hover:shadow-md">
        <CardContent class="p-6 text-center">
          <div class="text-3xl font-bold leading-none text-amber-600">{{ cardStats.times_used || 0 }}</div>
          <div class="mt-2 text-sm text-muted-foreground">总使用次数</div>
        </CardContent>
      </Card>
    </div>

    <!-- 卡片列表 -->
    <Card class="shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">卡片列表</CardTitle>
      </CardHeader>
      <CardContent>
      <DataTable
        v-loading="loading"
        :data="cards"
        class="w-full"
        @selection-change="handleSelectionChange"
        @sort-change="handleSortChange"
      >
        <DataColumn type="selection" width="55" />
        
        <DataColumn prop="id" label="ID" width="80" sortable="custom" />
        
        <DataColumn prop="card_number_masked" label="卡号" width="200" />
        
        <DataColumn prop="exp_month" label="过期月" width="100" />
        
        <DataColumn prop="exp_year" label="过期年" width="100" />
        
        <DataColumn prop="card_holder" label="持卡人" width="150" />
        
        <DataColumn prop="times_used" label="已使用" width="100">
          <template #default="{ row }">
            <span
              class="font-semibold"
              :class="row.times_used >= row.max_uses ? 'text-rose-600' : 'text-emerald-600'"
            >
              {{ row.times_used }} / {{ row.max_uses }}
            </span>
          </template>
        </DataColumn>

        <DataColumn prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <Tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '可用' : '禁用' }}
            </Tag>
          </template>
        </DataColumn>

        <DataColumn prop="created_at" label="创建时间" width="180" sortable="custom" />

        <DataColumn label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <Button size="small" @click="showEditDialog(row)">
              <Icon><Edit /></Icon>
              编辑
            </Button>
            <Button
              size="small"
              :type="row.is_active ? 'warning' : 'success'"
              @click="toggleActive(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </Button>
            <Button size="small"  variant="destructive" type="button" @click="deleteCard(row.id)">
              <Icon><Delete /></Icon>
              删除
            </Button>
          </template>
        </DataColumn>
      </DataTable>

      <!-- 分页 -->
      <div class="mt-5 flex justify-end">
        <Paginator
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
      </CardContent>
    </Card>

    <!-- 添加/编辑卡片对话框 -->
    <Modal
      v-model="dialogVisible"
      :title="dialogMode === 'add' ? '添加卡片' : '编辑卡片'"
      width="500px"
    >
      <SimpleForm :model="form" :rules="formRules" ref="formRef" label-width="100px">
        <SimpleFormItem label="卡号" prop="card_number">
          <TextInput v-model="form.card_number" placeholder="请输入卡号" maxlength="16" />
        </SimpleFormItem>

        <SimpleFormItem label="过期月" prop="exp_month">
          <SelectNative v-model="form.exp_month" placeholder="请选择月份">
            <SelectOption v-for="month in 12" :key="month" :label="String(month).padStart(2, '0')" :value="String(month).padStart(2, '0')" />
          </SelectNative>
        </SimpleFormItem>

        <SimpleFormItem label="过期年" prop="exp_year">
          <SelectNative v-model="form.exp_year" placeholder="请选择年份">
            <SelectOption v-for="year in 10" :key="year" :label="String(new Date().getFullYear() - 2000 + year)" :value="String(new Date().getFullYear() - 2000 + year)" />
          </SelectNative>
        </SimpleFormItem>

        <SimpleFormItem label="CVV" prop="cvv">
          <TextInput v-model="form.cvv" placeholder="请输入CVV" maxlength="4" />
        </SimpleFormItem>

        <SimpleFormItem label="持卡人">
          <TextInput v-model="form.card_holder" placeholder="请输入持卡人姓名（可选）" />
        </SimpleFormItem>

        <SimpleFormItem label="账单地址">
          <TextInput v-model="form.billing_address" type="textarea" :rows="3" placeholder="请输入账单地址（可选）" />
        </SimpleFormItem>

        <SimpleFormItem label="最大使用次数">
          <NumberInput v-model="form.max_uses" :min="1" :max="100" />
        </SimpleFormItem>

        <SimpleFormItem label="状态">
          <Toggle v-model="form.is_active" active-text="可用" inactive-text="禁用" />
        </SimpleFormItem>
      </SimpleForm>

      <template #footer>
        <Button @click="dialogVisible = false">取消</Button>
        <Button  variant="default" type="button" @click="handleSubmit" :loading="submitting">
          确定
        </Button>
      </template>
    </Modal>

    <!-- 批量导入对话框 -->
    <Modal
      v-model="batchImportVisible"
      title="批量导入卡片"
      width="600px"
    >
      <InfoAlert
        title="导入格式说明"
        type="info"
        :closable="false"
        class="mb-5"
      >
        <div>每行一张卡片，格式：卡号 过期月 过期年 CVV [持卡人]</div>
        <div>示例：4111111111111111 12 25 123 John Doe</div>
      </InfoAlert>

      <TextInput
        v-model="batchImportText"
        type="textarea"
        :rows="10"
        placeholder="请输入卡片信息，每行一张卡片"
      />

      <template #footer>
        <Button @click="batchImportVisible = false">取消</Button>
        <Button  variant="default" type="button" @click="handleBatchImport" :loading="importing">
          导入
        </Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import type { ElFormRules } from '@/components/app/symbols'
import { 
  Search, 
  RefreshLeft, 
  Plus,
  Upload,
  Delete,
  Edit
} from '@/icons'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  getCards,
  createCard,
  updateCard,
  deleteCard as deleteCardApi,
  batchImportCards,
  batchDeleteCards,
  getCardStats
} from '@/api/google_business'

// 搜索表单
const searchForm = ref({
  search: '',
  is_active: undefined as boolean | undefined
})

// 分页配置
const pagination = ref({
  page: 1,
  page_size: 20,
  total: 0
})

// 排序配置
const ordering = ref('-created_at')

// 数据
const cards = ref<any[]>([])
const cardStats = ref<any>({})
const loading = ref(false)
const selectedIds = ref<number[]>([])

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'add' | 'edit'>('add')
const form = ref({
  card_number: '',
  exp_month: '',
  exp_year: '',
  cvv: '',
  card_holder: '',
  billing_address: '',
  max_uses: 1,
  is_active: true
})
type ElFormExpose = {
  validate: (cb?: (valid: boolean) => void | Promise<void>) => Promise<boolean>
  resetFields?: () => void
}

const formRef = ref<ElFormExpose | null>(null)
const submitting = ref(false)
const editingId = ref<number | null>(null)

// 表单验证规则
const formRules: ElFormRules = {
  card_number: [
    { required: true, message: '请输入卡号', trigger: 'blur' },
    { pattern: /^\d{13,19}$/, message: '卡号格式不正确', trigger: 'blur' }
  ],
  exp_month: [
    { required: true, message: '请选择过期月份', trigger: 'change' }
  ],
  exp_year: [
    { required: true, message: '请选择过期年份', trigger: 'change' }
  ],
  cvv: [
    { required: true, message: '请输入CVV', trigger: 'blur' },
    { pattern: /^\d{3,4}$/, message: 'CVV格式不正确', trigger: 'blur' }
  ]
}

// 批量导入
const batchImportVisible = ref(false)
const batchImportText = ref('')
const importing = ref(false)

// 加载卡片列表
const loadCards = async () => {
  loading.value = true
  try {
    const res = await getCards({
      page: pagination.value.page,
      page_size: pagination.value.page_size,
      search: searchForm.value.search || undefined,
      is_active: searchForm.value.is_active,
      ordering: ordering.value
    })

    cards.value = res.data?.results || []
    pagination.value.total = res.data?.count || 0
  } catch (error: any) {
    console.error('加载卡片列表失败:', error)
    ElMessage.error(error.response?.data?.error || '加载卡片列表失败')
  } finally {
    loading.value = false
  }
}

// 加载统计
const loadStats = async () => {
  try {
    const res = await getCardStats()
    cardStats.value = res.data || {}
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.value.page = 1
  loadCards()
}

// 重置
const handleReset = () => {
  searchForm.value = {
    search: '',
    is_active: undefined
  }
  pagination.value.page = 1
  ordering.value = '-created_at'
  loadCards()
}

// 排序
const handleSortChange = ({ prop, order }: any) => {
  if (order === 'ascending') {
    ordering.value = prop
  } else if (order === 'descending') {
    ordering.value = `-${prop}`
  } else {
    ordering.value = '-created_at'
  }
  loadCards()
}

// 分页
const handleSizeChange = () => {
  pagination.value.page = 1
  loadCards()
}

const handlePageChange = () => {
  loadCards()
}

// 选择变化
const handleSelectionChange = (selection: any[]) => {
  selectedIds.value = selection.map(item => item.id)
}

// 显示添加对话框
const showAddDialog = () => {
  dialogMode.value = 'add'
  editingId.value = null
  form.value = {
    card_number: '',
    exp_month: '',
    exp_year: '',
    cvv: '',
    card_holder: '',
    billing_address: '',
    max_uses: 1,
    is_active: true
  }
  dialogVisible.value = true
}

// 显示编辑对话框
const showEditDialog = (card: any) => {
  dialogMode.value = 'edit'
  editingId.value = card.id
  form.value = {
    card_number: '',  // 不显示完整卡号
    exp_month: card.exp_month,
    exp_year: card.exp_year,
    cvv: '',  // 不显示CVV
    card_holder: card.card_holder || '',
    billing_address: card.billing_address || '',
    max_uses: card.max_uses || 1,
    is_active: card.is_active
  }
  dialogVisible.value = true
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    submitting.value = true

    if (dialogMode.value === 'add') {
      await createCard(form.value)
      ElMessage.success('卡片添加成功')
    } else {
      // 编辑时不更新卡号和CVV
      const updateData: any = {
        exp_month: form.value.exp_month,
        exp_year: form.value.exp_year,
        card_holder: form.value.card_holder,
        billing_address: form.value.billing_address,
        max_uses: form.value.max_uses,
        is_active: form.value.is_active
      }
      
      // 如果填写了CVV，则更新
      if (form.value.cvv) {
        updateData.cvv = form.value.cvv
      }

      await updateCard(editingId.value!, updateData)
      ElMessage.success('卡片更新成功')
    }

    dialogVisible.value = false
    loadCards()
    loadStats()
  } catch (error: any) {
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    }
  } finally {
    submitting.value = false
  }
}

// 切换启用状态
const toggleActive = async (card: any) => {
  try {
    await updateCard(card.id, { is_active: !card.is_active })
    ElMessage.success(`卡片已${card.is_active ? '禁用' : '启用'}`)
    loadCards()
    loadStats()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '操作失败')
  }
}

// 删除卡片
const deleteCard = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要删除此卡片吗？删除后无法恢复！', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'error'
    })

    await deleteCardApi(id)
    ElMessage.success('卡片已删除')
    loadCards()
    loadStats()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '删除失败')
    }
  }
}

// 批量删除
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 张卡片吗？删除后无法恢复！`, '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'error'
    })

    await batchDeleteCards({ ids: selectedIds.value })
    ElMessage.success('批量删除成功')
    selectedIds.value = []
    loadCards()
    loadStats()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '批量删除失败')
    }
  }
}

// 显示批量导入对话框
const showBatchImportDialog = () => {
  batchImportText.value = ''
  batchImportVisible.value = true
}

// 批量导入
const handleBatchImport = async () => {
  if (!batchImportText.value.trim()) {
    ElMessage.warning('请输入卡片信息')
    return
  }

  try {
    importing.value = true

    const lines = batchImportText.value.trim().split('\n')
    const cardsToImport: any[] = []

    for (const line of lines) {
      const parts = line.trim().split(/\s+/)
      if (parts.length >= 4) {
        cardsToImport.push({
          card_number: parts[0],
          exp_month: parts[1],
          exp_year: parts[2],
          cvv: parts[3],
          card_holder: parts.slice(4).join(' ') || undefined
        })
      }
    }

    if (cardsToImport.length === 0) {
      ElMessage.warning('没有有效的卡片信息')
      return
    }

    await batchImportCards({ cards: cardsToImport })
    ElMessage.success(`成功导入 ${cardsToImport.length} 张卡片`)
    batchImportVisible.value = false
    loadCards()
    loadStats()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.error || '批量导入失败')
  } finally {
    importing.value = false
  }
}

// 组件挂载
onMounted(async () => {
  await Promise.all([loadCards(), loadStats()])
})
</script>
