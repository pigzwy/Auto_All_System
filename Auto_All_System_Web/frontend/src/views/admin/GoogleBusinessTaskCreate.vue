<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="px-4 py-3">
        <PageHeader @back="$router.push('/admin/google-business/tasks')" content="创建任务" />
      </CardContent>
    </Card>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="p-6">
        <SimpleForm :model="form" :rules="rules" ref="formRef" label-width="120px">
        <!-- 任务类型 -->
        <SimpleFormItem label="任务类型" prop="task_type">
          <RadioGroup v-model="form.task_type" @change="handleTaskTypeChange">
            <RadioButton label="login">
              <div class="space-y-1 p-2 text-left">
                <div class="font-semibold">登录 (1积分)</div>
                <div class="text-xs text-muted-foreground">自动登录Google账号</div>
              </div>
            </RadioButton>
            <RadioButton label="get_link">
              <div class="space-y-1 p-2 text-left">
                <div class="font-semibold">获取链接 (2积分)</div>
                <div class="text-xs text-muted-foreground">获取SheerID验证链接</div>
              </div>
            </RadioButton>
            <RadioButton label="verify">
              <div class="space-y-1 p-2 text-left">
                <div class="font-semibold">SheerID验证 (5积分)</div>
                <div class="text-xs text-muted-foreground">批量验证学生资格</div>
              </div>
            </RadioButton>
            <RadioButton label="bind_card">
              <div class="space-y-1 p-2 text-left">
                <div class="font-semibold">绑卡订阅 (10积分)</div>
                <div class="text-xs text-muted-foreground">绑定卡片并订阅</div>
              </div>
            </RadioButton>
            <RadioButton label="one_click">
              <div class="space-y-1 p-2 text-left">
                <div class="font-semibold">一键到底 (18积分)</div>
                <div class="text-xs text-muted-foreground">登录→获取链接→验证→绑卡</div>
              </div>
            </RadioButton>
          </RadioGroup>
        </SimpleFormItem>

        <!-- 任务配置 -->
        <Divider content-position="left">任务配置</Divider>

        <!-- SheerID API密钥（verify和one_click需要） -->
        <SimpleFormItem
          v-if="['verify', 'one_click'].includes(form.task_type)"
          label="SheerID API Key"
          prop="config.api_key"
        >
          <TextInput
            v-model="form.config.api_key"
            placeholder="请输入SheerID API密钥"
            show-password
          >
            <template #append>
              <Button @click="loadApiKey">从配置加载</Button>
            </template>
          </TextInput>
          <div class="mt-2 text-xs text-muted-foreground">
            用于绕过hCaptcha验证，提高成功率
          </div>
        </SimpleFormItem>

        <!-- 卡片选择（bind_card和one_click需要） -->
        <SimpleFormItem
          v-if="['bind_card', 'one_click'].includes(form.task_type)"
          label="选择卡片"
          prop="config.card_id"
        >
          <SelectNative v-model="form.config.card_id" placeholder="请选择卡片" filterable>
            <SelectOption
              v-for="card in cards"
              :key="card.id"
              :label="`${card.card_number_masked} (可用次数: ${card.max_uses - card.times_used})`"
              :value="card.id"
              :disabled="card.times_used >= card.max_uses || !card.is_active"
            />
          </SelectNative>
          <div class="mt-2 text-xs text-muted-foreground">
            选择要用于绑卡的信用卡
          </div>
        </SimpleFormItem>

        <!-- 账号选择 -->
        <Divider content-position="left">选择账号</Divider>

        <!-- 账号筛选 -->
        <SimpleFormItem label="账号筛选">
          <RadioGroup v-model="accountFilter" @change="loadAccounts">
            <RadioButton label="all">全部账号</RadioButton>
            <RadioButton label="pending">待验证</RadioButton>
            <RadioButton label="verified">已验证未绑卡</RadioButton>
            <RadioButton label="subscribed">已绑卡</RadioButton>
          </RadioGroup>
        </SimpleFormItem>

        <SimpleFormItem label="账号列表" prop="account_ids">
          <Transfer
            v-model="form.account_ids"
            :data="accounts"
            :titles="['可选账号', '已选账号']"
            filterable
            :filter-method="filterAccount"
            filter-placeholder="搜索账号"
          >
            <template #default="{ option }">
              <span>{{ option.label }}</span>
              <span class="ml-2 text-xs text-muted-foreground">
                ({{ option.status }})
              </span>
            </template>
          </Transfer>
          <div class="mt-2 text-xs text-muted-foreground">
            已选择 <strong>{{ form.account_ids.length }}</strong> 个账号
          </div>
        </SimpleFormItem>

        <!-- 费用预估 -->
        <InfoAlert
          :title="`预估费用: ${estimatedCost} 积分`"
          type="info"
          :closable="false"
          show-icon
        >
          <template #default>
            <div>
              任务类型: {{ getTaskTypeName(form.task_type) }} ({{ getTaskCost(form.task_type) }} 积分/账号)
            </div>
            <div>
              选中账号数: {{ form.account_ids.length }}
            </div>
            <div class="mt-2 font-semibold">
              总费用: {{ estimatedCost }} 积分
            </div>
          </template>
        </InfoAlert>

        <!-- 提交按钮 -->
        <SimpleFormItem class="mt-8">
          <Button variant="success" type="button" @click="handleSubmit" :loading="submitting">
            <Icon><Check /></Icon>
            创建任务
          </Button>
          <Button @click="handleReset">
            <Icon><RefreshLeft /></Icon>
            重置
          </Button>
          <Button @click="$router.back()">
            <Icon><Close /></Icon>
            取消
          </Button>
        </SimpleFormItem>
        </SimpleForm>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { useRouter } from 'vue-router'
import type { ElFormRules } from '@/components/app/symbols'
import { Card, CardContent } from '@/components/ui/card'
import {
  getGoogleAccounts,
  getCards,
  createTask,
  getPluginConfig
} from '@/api/google_business'

const router = useRouter()
type ElFormExpose = {
  validate: (cb?: (valid: boolean) => void | Promise<void>) => Promise<boolean>
  resetFields?: () => void
}

const formRef = ref<ElFormExpose | null>(null)

// 表单数据
const form = ref({
  task_type: 'login',
  account_ids: [] as number[],
  config: {
    api_key: '',
    card_id: undefined as number | undefined
  }
})

// 表单验证规则
const rules: ElFormRules = {
  task_type: [
    { required: true, message: '请选择任务类型', trigger: 'change' }
  ],
  account_ids: [
    { required: true, message: '请至少选择一个账号', trigger: 'change' },
    { type: 'array', min: 1, message: '请至少选择一个账号', trigger: 'change' }
  ],
  'config.api_key': [
    {
      validator: (_rule: any, value: any, callback: any) => {
        if (['verify', 'one_click'].includes(form.value.task_type) && !value) {
          callback(new Error('请输入SheerID API密钥'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  'config.card_id': [
    {
      validator: (_rule: any, value: any, callback: any) => {
        if (['bind_card', 'one_click'].includes(form.value.task_type) && !value) {
          callback(new Error('请选择卡片'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// 数据
const accounts = ref<any[]>([])
const cards = ref<any[]>([])
const accountFilter = ref('all')
const submitting = ref(false)

// 预估费用
const estimatedCost = computed(() => {
  const costPerAccount = getTaskCost(form.value.task_type)
  return costPerAccount * form.value.account_ids.length
})

// 获取任务费用
const getTaskCost = (taskType: string) => {
  const costs: Record<string, number> = {
    login: 1,
    get_link: 2,
    verify: 5,
    bind_card: 10,
    one_click: 18
  }
  return costs[taskType] || 0
}

// 获取任务类型名称
const getTaskTypeName = (type: string) => {
  const map: Record<string, string> = {
    login: '登录',
    get_link: '获取链接',
    verify: 'SheerID验证',
    bind_card: '绑卡订阅',
    one_click: '一键到底'
  }
  return map[type] || type
}

// 加载账号列表
const loadAccounts = async () => {
  try {
    const params: any = {
      page: 1,
      page_size: 1000
    }

    if (accountFilter.value !== 'all') {
      params.status = accountFilter.value
    }

    const res = await getGoogleAccounts(params)
    const accountList = res.data?.results || []

    accounts.value = accountList.map((acc: any) => ({
      key: acc.id,
      label: acc.email,
      status: acc.status || 'unknown'
    }))
  } catch (error: any) {
    console.error('加载账号列表失败:', error)
    ElMessage.error('加载账号列表失败')
  }
}

// 加载卡片列表
const loadCards = async () => {
  try {
    const res = await getCards({ page: 1, page_size: 1000, is_active: true })
    cards.value = res.data?.results || []
  } catch (error: any) {
    console.error('加载卡片列表失败:', error)
    ElMessage.error('加载卡片列表失败')
  }
}

// 从配置加载API密钥
const loadApiKey = async () => {
  try {
    const res = await getPluginConfig()
    if (res.data?.sheerid_api_key) {
      form.value.config.api_key = res.data.sheerid_api_key
      ElMessage.success('API密钥已加载')
    } else {
      ElMessage.warning('配置中未找到API密钥')
    }
  } catch (error: any) {
    ElMessage.error('加载API密钥失败')
  }
}

// 任务类型变化
const handleTaskTypeChange = () => {
  // 清空不需要的配置项
  if (!['verify', 'one_click'].includes(form.value.task_type)) {
    form.value.config.api_key = ''
  }
  if (!['bind_card', 'one_click'].includes(form.value.task_type)) {
    form.value.config.card_id = undefined
  }
}

// 账号筛选
const filterAccount = (query: string, item: any) => {
  return item.label.toLowerCase().includes(query.toLowerCase())
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()

    submitting.value = true

    const data: any = {
      task_type: form.value.task_type,
      account_ids: form.value.account_ids,
      config: {}
    }

    // 只包含需要的配置项
    if (['verify', 'one_click'].includes(form.value.task_type) && form.value.config.api_key) {
      data.config.api_key = form.value.config.api_key
    }
    if (['bind_card', 'one_click'].includes(form.value.task_type) && form.value.config.card_id) {
      data.config.card_id = form.value.config.card_id
    }

    await createTask(data)

    ElMessage.success('任务创建成功')
    router.push('/admin/google-business/tasks')
  } catch (error: any) {
    if (error.response?.data?.error) {
      ElMessage.error(error.response.data.error)
    } else if (error) {
      console.error('创建任务失败:', error)
    }
  } finally {
    submitting.value = false
  }
}

// 重置表单
const handleReset = () => {
  if (formRef.value) {
    formRef.value.resetFields?.()
  }
  form.value = {
    task_type: 'login',
    account_ids: [],
    config: {
      api_key: '',
      card_id: undefined
    }
  }
}

// 组件挂载
onMounted(async () => {
  await Promise.all([loadAccounts(), loadCards()])
})
</script>

<style scoped>
:deep(.el-radio-button__inner) {
  padding: 0;
  height: auto;
}

:deep(.el-transfer .el-transfer-panel) {
  width: 400px;
}
</style>
