<template>
  <div class="space-y-6 p-5">
    <div>
      <h1 class="text-2xl font-semibold text-foreground">支付方式配置</h1>
      <p class="mt-1 text-sm text-muted-foreground">管理支付网关、启用状态、手续费与金额范围。</p>
    </div>

    <Card class="shadow-sm">
      <CardContent class="p-6">
      <DataTable :data="configs" v-loading="loading" stripe class="w-full">
        <DataColumn prop="id" label="ID" width="60" />
        <DataColumn prop="name" label="支付方式" width="150">
          <template #default="{ row }">
            <span class="text-base font-medium">{{ row.icon }} {{ row.name }}</span>
          </template>
        </DataColumn>
        <DataColumn prop="gateway" label="网关标识" width="120">
          <template #default="{ row }">
            <code class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-primary">{{ row.gateway }}</code>
          </template>
        </DataColumn>
        <DataColumn label="启用状态" width="100">
          <template #default="{ row }">
            <Toggle 
              v-model="row.is_enabled" 
              @change="toggleEnable(row)"
              active-color="#13ce66"
              inactive-color="#ff4949"
            />
          </template>
        </DataColumn>
        <DataColumn prop="sort_order" label="排序" width="80" />
        <DataColumn prop="fee_rate" label="手续费率" width="100">
          <template #default="{ row }">
            {{ (row.fee_rate * 100).toFixed(2) }}%
          </template>
        </DataColumn>
        <DataColumn label="金额范围" width="180">
          <template #default="{ row }">
            ¥{{ row.min_amount }} - ¥{{ row.max_amount }}
          </template>
        </DataColumn>
        <DataColumn prop="description" label="说明" min-width="200" show-overflow-tooltip />
        <DataColumn label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <Button text variant="ghost" class="text-warning hover:text-warning" type="button" @click="editConfig(row)">编辑</Button>
          </template>
        </DataColumn>
      </DataTable>
      </CardContent>
    </Card>

    <!-- 编辑对话框 -->
    <Modal v-model="showEditDialog" title="编辑支付配置" width="600px">
      <SimpleForm :model="editForm" label-width="120px">
        <SimpleFormItem label="支付方式名称">
          <TextInput v-model="editForm.name" />
        </SimpleFormItem>
        <SimpleFormItem label="图标">
          <TextInput v-model="editForm.icon" placeholder="emoji或图片URL" />
        </SimpleFormItem>
        <SimpleFormItem label="最小金额">
          <NumberInput v-model="editForm.min_amount" :min="0" :precision="2" />
          <span class="ml-2 text-sm text-muted-foreground">元</span>
        </SimpleFormItem>
        <SimpleFormItem label="最大金额">
          <NumberInput v-model="editForm.max_amount" :min="0" :precision="2" />
          <span class="ml-2 text-sm text-muted-foreground">元</span>
        </SimpleFormItem>
        <SimpleFormItem label="手续费率">
          <NumberInput v-model="editForm.fee_rate" :min="0" :max="1" :step="0.001" :precision="4" />
          <span class="ml-2 text-sm text-muted-foreground">{{ (editForm.fee_rate * 100).toFixed(2) }}%</span>
        </SimpleFormItem>
        <SimpleFormItem label="排序">
          <NumberInput v-model="editForm.sort_order" :min="0" />
        </SimpleFormItem>
        <SimpleFormItem label="说明">
          <TextInput v-model="editForm.description" type="textarea" :rows="2" />
        </SimpleFormItem>
      </SimpleForm>
      <template #footer>
        <Button @click="showEditDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="handleSave" :loading="saving">保存</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { paymentsApi } from '@/api/payments'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const saving = ref(false)
const configs = ref<any[]>([])
const showEditDialog = ref(false)
const currentConfig = ref<any>(null)

const editForm = reactive({
  id: 0,
  name: '',
  icon: '',
  min_amount: 0,
  max_amount: 0,
  fee_rate: 0,
  sort_order: 0,
  description: ''
})

const fetchConfigs = async () => {
  loading.value = true
  try {
    const response: any = await paymentsApi.getAllPaymentConfigs()
    // 处理两种响应格式：直接数组 或 包装格式
    configs.value = Array.isArray(response) ? response : (response.data || response)
  } catch (error) {
    console.error('获取支付配置失败:', error)
    ElMessage.error('获取支付配置失败')
  } finally {
    loading.value = false
  }
}

const toggleEnable = async (row: any) => {
  const originalValue = !row.is_enabled
  try {
    await paymentsApi.patchPaymentConfig(row.id, {
      is_enabled: row.is_enabled
    })
    ElMessage.success(`${row.name} 已${row.is_enabled ? '启用' : '禁用'}`)
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error('操作失败')
    // 恢复原值
    row.is_enabled = originalValue
  }
}

const editConfig = (row: any) => {
  currentConfig.value = row
  Object.assign(editForm, {
    id: row.id,
    name: row.name,
    icon: row.icon,
    min_amount: parseFloat(row.min_amount),
    max_amount: parseFloat(row.max_amount),
    fee_rate: parseFloat(row.fee_rate),
    sort_order: row.sort_order,
    description: row.description || ''
  })
  showEditDialog.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    await paymentsApi.updatePaymentConfig(editForm.id, {
      name: editForm.name,
      icon: editForm.icon,
      min_amount: editForm.min_amount,
      max_amount: editForm.max_amount,
      fee_rate: editForm.fee_rate,
      sort_order: editForm.sort_order,
      description: editForm.description
    })
    ElMessage.success('保存成功')
    showEditDialog.value = false
    await fetchConfigs()
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>
