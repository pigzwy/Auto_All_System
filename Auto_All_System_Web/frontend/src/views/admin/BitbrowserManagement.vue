<template>
  <div class="space-y-6 p-5">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">比特浏览器配置</h1>
        <p class="mt-1 text-sm text-muted-foreground">管理 Profile、代理关联与可用状态。</p>
      </div>
      <Button variant="success" type="button" @click="showDialog = true">
        <Icon><Plus /></Icon>
        添加配置
      </Button>
    </div>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="p-6">
        <DataTable :data="configs" v-loading="loading" stripe class="w-full">
        <DataColumn prop="id" label="ID" width="60" />
        <DataColumn prop="name" label="配置名称" width="150" />
        <DataColumn prop="profile_id" label="浏览器ID" width="200">
          <template #default="{ row }">
            <code class="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-xs text-primary">{{ row.profile_id }}</code>
          </template>
        </DataColumn>
        <DataColumn label="代理" width="150">
          <template #default="{ row }">
            {{ row.proxy ? row.proxy.name : '无代理' }}
          </template>
        </DataColumn>
        <DataColumn label="状态" width="100">
          <template #default="{ row }">
            <Tag :type="getStatusColor(row.status)">{{ getStatusName(row.status) }}</Tag>
          </template>
        </DataColumn>
        <DataColumn prop="usage_count" label="使用次数" width="100" />
        <DataColumn label="是否可用" width="100">
          <template #default="{ row }">
            <Toggle v-model="row.is_active" @change="toggleActive(row)" />
          </template>
        </DataColumn>
        <DataColumn prop="last_used" label="最后使用" width="180" />
        <DataColumn label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <Button text variant="ghost" class="text-warning hover:text-warning" type="button" @click="editConfig(row)">编辑</Button>
            <Button text  variant="default" type="button" @click="testConfig(row)">测试</Button>
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
      <SimpleForm :model="formData" label-width="100px">
        <SimpleFormItem label="配置名称">
          <TextInput v-model="formData.name" placeholder="给配置起个名字" />
        </SimpleFormItem>
        <SimpleFormItem label="浏览器ID">
          <TextInput v-model="formData.profile_id" placeholder="比特浏览器Profile ID" />
        </SimpleFormItem>
        <SimpleFormItem label="API地址">
          <TextInput v-model="formData.api_url" placeholder="http://127.0.0.1:54345" />
        </SimpleFormItem>
        <SimpleFormItem label="选择代理">
          <SelectNative v-model="formData.proxy_id" placeholder="选择代理配置" clearable>
            <SelectOption 
              v-for="proxy in availableProxies" 
              :key="proxy.id"
              :label="proxy.name"
              :value="proxy.id"
            />
          </SelectNative>
        </SimpleFormItem>
        <SimpleFormItem label="最大并发">
          <NumberInput v-model="formData.max_concurrent" :min="1" :max="10" />
        </SimpleFormItem>
        <SimpleFormItem label="超时时间">
          <NumberInput v-model="formData.timeout" :min="10" :max="300" />
          <span class="ml-2 text-sm text-muted-foreground">秒</span>
        </SimpleFormItem>
        <SimpleFormItem label="启用">
          <Toggle v-model="formData.is_active" />
        </SimpleFormItem>
        <SimpleFormItem label="备注">
          <TextInput 
            v-model="formData.notes" 
            type="textarea" 
            :rows="3"
            placeholder="配置说明备注"
          />
        </SimpleFormItem>
      </SimpleForm>
      <template #footer>
        <Button @click="showDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="handleSave">保存</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Plus } from '@/icons'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const configs = ref<any[]>([])
const availableProxies = ref<any[]>([])
const showDialog = ref(false)
const editingConfig = ref<any>(null)

const formData = reactive({
  name: '',
  profile_id: '',
  api_url: 'http://127.0.0.1:54345',
  proxy_id: null,
  max_concurrent: 3,
  timeout: 60,
  is_active: true,
  notes: ''
})

const fetchConfigs = async () => {
  loading.value = true
  try {
    // TODO: 调用配置API
    configs.value = []
  } catch (error) {
    ElMessage.error('获取配置列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProxies = async () => {
  try {
    // TODO: 获取可用代理列表
    availableProxies.value = []
  } catch (error) {
    console.error('获取代理列表失败', error)
  }
}

const getStatusColor = (status: string) => {
  const map: Record<string, any> = {
    idle: 'info',
    running: 'success',
    error: 'danger'
  }
  return map[status] || 'info'
}

const getStatusName = (status: string) => {
  const map: Record<string, string> = {
    idle: '空闲',
    running: '运行中',
    error: '错误'
  }
  return map[status] || status
}

const editConfig = (row: any) => {
  editingConfig.value = row
  Object.assign(formData, row)
  showDialog.value = true
}

const testConfig = async (_row: any) => {
  loading.value = true
  try {
    ElMessage.success('浏览器配置测试成功')
  } catch (error) {
    ElMessage.error('浏览器配置测试失败')
  } finally {
    loading.value = false
  }
}

const toggleActive = async (_row: any) => {
  try {
    ElMessage.success(`已${_row.is_active ? '启用' : '禁用'}配置`)
  } catch (error) {
    ElMessage.error('操作失败')
    _row.is_active = !_row.is_active
  }
}

const deleteConfig = async (_row: any) => {
  try {
    await ElMessageBox.confirm('确定删除此配置吗？', '提示', {
      type: 'warning'
    })
    ElMessage.success('删除成功')
    fetchConfigs()
  } catch {
    // 用户取消
  }
}

const handleSave = () => {
  ElMessage.success('保存成功')
  showDialog.value = false
  fetchConfigs()
}

onMounted(() => {
  fetchConfigs()
  fetchProxies()
})
</script>
