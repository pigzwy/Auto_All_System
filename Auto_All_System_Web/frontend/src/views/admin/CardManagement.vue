<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">虚拟卡管理</h1>
        <p class="mt-1 text-sm text-muted-foreground">卡池维护、批量导入、卡密激活与 API 配置管理。</p>
      </div>
      <ButtonGroup>
        <Button variant="success" type="button" @click="showDialog = true">
          <Icon><Plus /></Icon>
          添加虚拟卡
        </Button>
        <Button variant="secondary" type="button" @click="showImportDialog = true">
          <Icon><Upload /></Icon>
          批量导入
        </Button>
        <Button  variant="secondary" type="button" @click="showRedeemDialog = true">
          <Icon><Key /></Icon>
          卡密激活
        </Button>
      </ButtonGroup>
    </div>

    <Panel shadow="hover" class="rounded-xl border border-border bg-card text-card-foreground shadow-sm">
      <div class="flex items-center gap-3 px-4 pt-4">
        <span class="text-sm text-muted-foreground">卡池筛选</span>
        <div class="inline-flex items-center rounded-lg border border-border bg-muted/40 p-1">
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-xs transition"
            :class="poolFilter === 'all' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
            @click="poolFilter = 'all'"
          >
            全部卡池
          </button>
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-xs transition"
            :class="poolFilter === 'public' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
            @click="poolFilter = 'public'"
          >
            公共卡池
          </button>
          <button
            type="button"
            class="rounded-md px-3 py-1.5 text-xs transition"
            :class="poolFilter === 'private' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
            @click="poolFilter = 'private'"
          >
            私有卡池
          </button>
        </div>
      </div>

      <div class="overflow-hidden rounded-xl border border-border">
        <DataTable :data="cards" v-loading="loading" stripe class="w-full">
        <DataColumn prop="id" label="ID" width="80" />
        <DataColumn label="卡号" width="200">
          <template #default="{ row }">
            <span class="font-mono font-medium">
              {{ row.card_number || row.masked_card_number }}
            </span>
          </template>
        </DataColumn>
        <DataColumn prop="card_holder" label="持卡人" width="150">
          <template #default="{ row }">
            {{ row.card_holder || '-' }}
          </template>
        </DataColumn>
        <DataColumn label="有效期" width="100">
          <template #default="{ row }">
            {{ String(row.expiry_month).padStart(2, '0') }}/{{ row.expiry_year }}
          </template>
        </DataColumn>
        <DataColumn label="卡类型/银行" width="180">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <Tag size="small" :type="row.card_type === 'visa' ? 'primary' : 'warning'">
                {{ row.card_type || 'Unknown' }}
              </Tag>
              <span class="text-xs text-muted-foreground">{{ row.bank_name || '' }}</span>
            </div>
          </template>
        </DataColumn>
        <DataColumn label="类型" width="100">
          <template #default="{ row }">
            <Tag :type="row.pool_type === 'public' ? 'primary' : 'success'">
              {{ row.pool_type_display || (row.pool_type === 'public' ? '公共' : '私有') }}
            </Tag>
          </template>
        </DataColumn>
        <DataColumn label="状态" width="100">
          <template #default="{ row }">
            <Tag :type="getDisplayStatusType(row)">{{ getDisplayStatus(row) }}</Tag>
          </template>
        </DataColumn>
        <DataColumn label="剩余时间" width="120">
          <template #default="{ row }">
            <template v-if="row.key_expire_time">
              <span v-if="isExpired(row.key_expire_time)" class="text-red-500">已过期</span>
              <span v-else class="text-green-600">{{ formatCountdown(row.key_expire_time) }}</span>
            </template>
            <span v-else class="text-muted-foreground">-</span>
          </template>
        </DataColumn>
        <DataColumn label="使用次数" width="120">
          <template #default="{ row }">
            <span>{{ row.use_count }}</span>
            <span class="text-muted-foreground"> / {{ row.max_use_count || '∞' }}</span>
          </template>
        </DataColumn>
        <DataColumn label="账单地址" min-width="200">
          <template #default="{ row }">
            <div v-if="row.billing_address && Object.keys(row.billing_address).length > 0" class="text-xs">
              <div>{{ row.billing_address.address_line1 || '-' }}</div>
              <div class="text-muted-foreground">
                {{ [row.billing_address.city, row.billing_address.state, row.billing_address.postal_code].filter(Boolean).join(', ') }}
              </div>
              <div class="text-muted-foreground/80">{{ row.billing_address.country || '' }}</div>
            </div>
            <span v-else class="text-muted-foreground text-xs">-</span>
          </template>
        </DataColumn>
        <DataColumn v-if="showOwnerColumn" label="所属者" width="120">
          <template #default="{ row }">
            <span v-if="row.owner_user">
              {{ row.owner_user_name || `用户${row.owner_user}` }}
            </span>
            <span v-else class="text-muted-foreground text-xs">公共卡池</span>
          </template>
        </DataColumn>
        <DataColumn label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <Button link  variant="warning" type="button" @click="editCard(row)">编辑</Button>
              <Button link  variant="destructive" type="button" @click="deleteCard(row)">删除</Button>
            </div>
          </template>
        </DataColumn>
        </DataTable>
      </div>

      <Paginator
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        class="mt-5 justify-center"
        @current-change="fetchCards"
      />
    </Panel>

    <!-- 添加对话框 -->
    <Modal v-model="showDialog" title="添加虚拟卡" width="500px">
      <SimpleForm :model="cardForm" label-width="100px">
        <SimpleFormItem label="卡号">
          <TextInput v-model="cardForm.card_number" placeholder="16位卡号" />
        </SimpleFormItem>
        <SimpleFormItem label="持卡人">
          <TextInput v-model="cardForm.card_holder" placeholder="持卡人姓名" />
        </SimpleFormItem>
        <SimpleFormItem label="过期月份">
          <NumberInput v-model="cardForm.expiry_month" :min="1" :max="12" />
        </SimpleFormItem>
        <SimpleFormItem label="过期年份">
          <NumberInput v-model="cardForm.expiry_year" :min="2024" :max="2099" />
        </SimpleFormItem>
        <SimpleFormItem label="CVV">
          <TextInput v-model="cardForm.cvv" placeholder="3-4位安全码" maxlength="4" />
        </SimpleFormItem>
        <SimpleFormItem label="卡池类型">
          <RadioGroup v-model="cardForm.pool_type">
            <Radio label="public">公共卡池</Radio>
            <Radio label="private">私有卡池</Radio>
          </RadioGroup>
        </SimpleFormItem>
      </SimpleForm>
      <template #footer>
        <Button @click="showDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="handleAddCard">保存</Button>
      </template>
    </Modal>

    <!-- 编辑对话框 -->
    <Modal v-model="showEditDialog" title="编辑虚拟卡" width="600px">
      <SimpleForm :model="editForm" label-width="100px">
        <SimpleFormItem label="卡号">
          <TextInput v-model="editForm.card_number" placeholder="16位卡号" />
        </SimpleFormItem>
        <SimpleFormItem label="持卡人">
          <TextInput v-model="editForm.card_holder" placeholder="持卡人姓名" />
        </SimpleFormItem>
        <SimpleFormItem label="过期月份">
          <NumberInput v-model="editForm.expiry_month" :min="1" :max="12" />
        </SimpleFormItem>
        <SimpleFormItem label="过期年份">
          <NumberInput v-model="editForm.expiry_year" :min="2024" :max="2099" />
        </SimpleFormItem>
        <SimpleFormItem label="CVV">
          <TextInput v-model="editForm.cvv" placeholder="3-4位安全码" maxlength="4" />
        </SimpleFormItem>
        <SimpleFormItem label="卡类型">
          <SelectNative v-model="editForm.card_type" class="w-40">
            <SelectOption label="Visa" value="Visa" />
            <SelectOption label="Master" value="Master" />
            <SelectOption label="American Express" value="American Express" />
            <SelectOption label="Discover" value="Discover" />
            <SelectOption label="Unknown" value="Unknown" />
          </SelectNative>
        </SimpleFormItem>
        <SimpleFormItem label="银行名称">
          <TextInput v-model="editForm.bank_name" placeholder="银行名称（可选）" />
        </SimpleFormItem>
        <SimpleFormItem label="卡池类型">
          <RadioGroup v-model="editForm.pool_type">
            <Radio label="public">公共卡池</Radio>
            <Radio label="private">私有卡池</Radio>
          </RadioGroup>
        </SimpleFormItem>
        <SimpleFormItem label="状态">
          <SelectNative v-model="editForm.status" class="w-40">
            <SelectOption label="可用" value="available" />
            <SelectOption label="使用中" value="in_use" />
            <SelectOption label="已用完" value="used" />
            <SelectOption label="无效" value="invalid" />
            <SelectOption label="已过期" value="expired" />
          </SelectNative>
        </SimpleFormItem>
        <SimpleFormItem label="最大使用次数">
          <NumberInput v-model="editForm.max_use_count" :min="1" :max="9999" />
        </SimpleFormItem>
        <SimpleFormItem label="卡密过期时间">
          <TextInput 
            v-model="editForm.key_expire_time" 
            placeholder="格式: 2026-01-28T15:39:20+00:00（留空表示永不过期）" 
          />
          <div class="text-xs text-muted-foreground mt-1">
            临时卡的过期时间，留空表示永不过期
          </div>
        </SimpleFormItem>
        <SimpleFormItem label="备注">
          <TextInput v-model="editForm.notes" type="textarea" :rows="2" placeholder="备注信息（可选）" />
        </SimpleFormItem>
      </SimpleForm>
      <template #footer>
        <Button @click="showEditDialog = false">取消</Button>
        <Button variant="default" type="button" @click="handleUpdateCard" :loading="updating">保存</Button>
      </template>
    </Modal>

    <!-- 批量导入对话框 -->
    <Modal v-model="showImportDialog" title="批量导入虚拟卡" width="700px">
      <InfoAlert type="info" :closable="false" class="mb-4">
        <template #title>
          <div>
            基础格式：
            <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">卡号 月份 年份 CVV</code>
            （空格分隔）
          </div>
          <div class="mt-2">
            扩展格式：
            <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">卡号 月份 年份 CVV | 持卡人 | 地址1 | 城市 | 州 | 邮编 | 国家</code>
          </div>
          <div class="mt-2">
            示例1：
            <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">4466164106155628 07 28 694</code>
          </div>
          <div class="mt-2">
            示例2：
            <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">5481087143137903 01 32 749 | TOM LEE | 123 Main St | Los Angeles | CA | 90001 | US</code>
          </div>
          <div class="mt-1 text-xs text-muted-foreground">💡 4开头自动识别为Visa，5开头自动识别为Master</div>
          <div class="mt-3 flex items-center gap-2">
            <span class="text-xs text-muted-foreground">示例模板</span>
            <div class="inline-flex items-center rounded-lg border border-border bg-muted/40 p-1">
              <button
                type="button"
                class="rounded-md px-3 py-1.5 text-xs transition"
                :class="importExampleMode === 'basic' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                @click="importExampleMode = 'basic'"
              >
                基础模板
              </button>
              <button
                type="button"
                class="rounded-md px-3 py-1.5 text-xs transition"
                :class="importExampleMode === 'address' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'"
                @click="importExampleMode = 'address'"
              >
                带地址模板
              </button>
            </div>
            <Button variant="outline" type="button" size="small" @click="fillImportExample">
              一键填充示例
            </Button>
          </div>
        </template>
      </InfoAlert>
      
      <SimpleForm :model="importForm" label-width="100px">
        <SimpleFormItem label="卡片数据">
          <TextInput
            v-model="importForm.cardsText"
            type="textarea"
            :rows="10"
            :placeholder="importPlaceholder"
          />
        </SimpleFormItem>
        <SimpleFormItem label="卡池类型">
          <RadioGroup v-model="importForm.pool_type">
            <Radio label="public">公共卡池</Radio>
            <Radio label="private">私有卡池</Radio>
          </RadioGroup>
        </SimpleFormItem>
      </SimpleForm>
      
      <div v-if="importResult" class="import-result">
        <InfoAlert :type="importResult.type" :closable="false">
          <template #title>
            <div>{{ importResult.message }}</div>
            <div v-if="importResult.data" class="mt-2 text-sm">
              总数：{{ importResult.data.total }} | 
              成功：{{ importResult.data.success }} | 
              失败：{{ importResult.data.failed }}
            </div>
          </template>
        </InfoAlert>
        <div v-if="importResult.data?.errors?.length" class="mt-3">
          <Collapse>
            <CollapseItem title="查看错误详情" name="errors">
              <div v-for="(error, index) in importResult.data.errors" :key="index" class="py-2 border-b border-border flex justify-between text-xs">
                <span>卡号: {{ error.card_number }}</span>
                <span class="text-destructive">错误: {{ error.error }}</span>
              </div>
            </CollapseItem>
          </Collapse>
        </div>
      </div>
      
      <template #footer>
        <Button @click="showImportDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="handleImport" :loading="importing">
          {{ importing ? '导入中...' : '开始导入' }}
        </Button>
      </template>
    </Modal>

    <!-- 卡密激活对话框 -->
    <Modal v-model="showRedeemDialog" title="卡密激活" width="500px" @open="loadApiConfigs">
      <InfoAlert type="info" :closable="false" class="mb-4">
        <template #title>
          <div>输入卡密后将调用激活接口获取完整卡信息（包含账单地址）</div>
        </template>
      </InfoAlert>
      
      <SimpleForm :model="redeemForm" label-width="100px">
        <SimpleFormItem label="API 配置">
          <SelectNative 
            v-model="redeemForm.config_id" 
            placeholder="选择 API 配置（默认使用系统默认）"
            clearable
            class="w-full"
          >
            <SelectOption 
              v-for="config in apiConfigs" 
              :key="config.id" 
              :label="config.name + (config.is_default ? ' (默认)' : '')" 
              :value="config.id"
            />
          </SelectNative>
          <div class="text-xs text-gray-400 mt-1">
            <Link type="primary" @click="showApiConfigDialog = true">管理 API 配置</Link>
          </div>
        </SimpleFormItem>
        <SimpleFormItem label="卡密">
          <TextInput 
            v-model="redeemForm.key_id" 
            placeholder="输入卡密 key_id"
            clearable
          />
        </SimpleFormItem>
        <SimpleFormItem label="卡池类型">
          <RadioGroup v-model="redeemForm.pool_type">
            <Radio label="public">公共卡池</Radio>
            <Radio label="private">私有卡池</Radio>
          </RadioGroup>
        </SimpleFormItem>
      </SimpleForm>
      
      <div v-if="redeemResult" class="redeem-result">
        <InfoAlert :type="redeemResult.type" :closable="false">
          <template #title>
            <div>{{ redeemResult.message }}</div>
          </template>
        </InfoAlert>
        <div v-if="redeemResult.data" class="card-info-preview">
          <Descriptions :column="2" border size="small" class="mt-3">
            <DescriptionsItem label="卡号">{{ redeemResult.data.masked_card_number }}</DescriptionsItem>
            <DescriptionsItem label="有效期">{{ String(redeemResult.data.expiry_month).padStart(2, '0') }}/{{ redeemResult.data.expiry_year }}</DescriptionsItem>
            <DescriptionsItem label="持卡人">{{ redeemResult.data.card_holder || '-' }}</DescriptionsItem>
            <DescriptionsItem label="卡类型">{{ redeemResult.data.card_type }}</DescriptionsItem>
            <DescriptionsItem label="地址" :span="2">
              {{ formatBillingAddress(redeemResult.data.billing_address) }}
            </DescriptionsItem>
          </Descriptions>
        </div>
      </div>
      
      <template #footer>
        <Button @click="showRedeemDialog = false">关闭</Button>
        <Button  variant="default" type="button" @click="handleRedeem" :loading="redeeming">
          {{ redeeming ? '激活中...' : '激活' }}
        </Button>
      </template>
    </Modal>

    <!-- API 配置管理对话框 -->
    <Modal v-model="showApiConfigDialog" title="API 配置管理" width="800px" @open="loadApiConfigs">
      <div class="mb-4">
        <Button  variant="default" type="button" size="small" @click="resetConfigForm(); showAddConfigForm = true">
          添加配置
        </Button>
      </div>
      
      <DataTable :data="apiConfigs" v-loading="loadingConfigs" stripe size="small">
        <DataColumn prop="name" label="名称" width="120">
          <template #default="{ row }">
            {{ row.name }}
            <Tag v-if="row.is_default" size="small" type="success" class="ml-1">默认</Tag>
          </template>
        </DataColumn>
        <DataColumn prop="redeem_url" label="激活接口" min-width="200">
          <template #default="{ row }">
            <span class="text-xs font-mono">{{ row.redeem_url }}</span>
          </template>
        </DataColumn>
        <DataColumn prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <Tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </Tag>
          </template>
        </DataColumn>
        <DataColumn label="操作" width="180">
          <template #default="{ row }">
            <Button link  variant="warning" type="button" size="small" @click="editApiConfig(row)">编辑</Button>
            <Button link  variant="default" type="button" size="small" v-if="!row.is_default" @click="setDefaultConfig(row)">设为默认</Button>
            <Button link  variant="destructive" type="button" size="small" @click="deleteApiConfig(row)">删除</Button>
          </template>
        </DataColumn>
      </DataTable>
      
      <!-- 添加/编辑配置表单 -->
      <Modal v-model="showAddConfigForm" :title="editingConfig ? '编辑配置' : '添加配置'" width="600px" append-to-body>
        <SimpleForm :model="configForm" label-width="120px">
          <SimpleFormItem label="配置名称" required>
            <TextInput v-model="configForm.name" placeholder="如: ActCard" />
          </SimpleFormItem>
          <SimpleFormItem label="激活接口 URL" required>
            <TextInput v-model="configForm.redeem_url" placeholder="https://actcard.xyz/api/keys/redeem" />
          </SimpleFormItem>
          <SimpleFormItem label="查询接口 URL">
            <TextInput v-model="configForm.query_url" placeholder="https://actcard.xyz/api/keys/query" />
          </SimpleFormItem>
          <SimpleFormItem label="请求方法">
            <SelectNative v-model="configForm.request_method" class="w-32">
              <SelectOption label="POST" value="POST" />
              <SelectOption label="GET" value="GET" />
            </SelectNative>
          </SimpleFormItem>
          <SimpleFormItem label="超时时间(秒)">
            <NumberInput v-model="configForm.timeout" :min="5" :max="120" />
          </SimpleFormItem>
          <SimpleFormItem label="请求头 (JSON)">
            <TextInput 
              v-model="configForm.request_headers_str" 
              type="textarea" 
              :rows="2"
              placeholder='{"Authorization": "Bearer xxx"}'
            />
          </SimpleFormItem>
          <SimpleFormItem label="响应映射 (JSON)">
            <TextInput 
              v-model="configForm.response_mapping_str" 
              type="textarea" 
              :rows="3"
              placeholder='{"data_path": "checkout", "fields": {"card_number": "card_number"}}'
            />
            <div class="text-xs text-muted-foreground mt-1">
              data_path: 响应中卡数据的路径；fields: 字段名映射
            </div>
          </SimpleFormItem>
          <SimpleFormItem label="启用">
            <Toggle v-model="configForm.is_active" />
          </SimpleFormItem>
          <SimpleFormItem label="备注">
            <TextInput v-model="configForm.notes" type="textarea" :rows="2" />
          </SimpleFormItem>
        </SimpleForm>
        <template #footer>
          <Button @click="showAddConfigForm = false">取消</Button>
          <Button  variant="default" type="button" @click="saveApiConfig" :loading="savingConfig">保存</Button>
        </template>
      </Modal>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted, watch } from 'vue'
import { cardsApi } from '@/api/cards'
import type { CardApiConfig } from '@/api/cards'
import { ElMessage } from '@/lib/element'
import { Plus, Upload, Key } from '@/icons'
import { useUserStore } from '@/stores/user'
import type { Card } from '@/types'

const loading = ref(false)
const cards = ref<Card[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const poolFilter = ref<'all' | 'public' | 'private'>('all')
const showDialog = ref(false)
const showImportDialog = ref(false)
const showRedeemDialog = ref(false)
const showEditDialog = ref(false)
const importing = ref(false)
const updating = ref(false)
const editingCardId = ref<number | null>(null)
const redeeming = ref(false)
const importResult = ref<any>(null)
const redeemResult = ref<any>(null)
const showOwnerColumn = ref(false)  // 是否显示所属者列

const cardForm = reactive({
  card_number: '',
  card_holder: '',
  expiry_month: 1,
  expiry_year: 2024,
  cvv: '',
  pool_type: 'public'
})

const importForm = reactive({
  cardsText: '',
  pool_type: 'public'
})

const importExampleMode = ref<'basic' | 'address'>('address')

const importPlaceholder = computed(() => {
  if (importExampleMode.value === 'basic') {
    return '粘贴卡片数据，每行一张卡\n4466164106155628 07 28 694\n5481087143137903 01 32 749'
  }
  return '粘贴卡片数据，每行一张卡\n4466164106155628 07 28 694 | TOM LEE | 123 Main St | Los Angeles | CA | 90001 | US\n5481087143137903 01 32 749 | JANE DOE | 500 5th Ave | New York | NY | 10018 | US'
})

const redeemForm = reactive({
  key_id: '',
  pool_type: 'public',
  config_id: undefined as number | undefined
})

const editForm = reactive({
  card_number: '',
  card_holder: '',
  expiry_month: 1,
  expiry_year: 2024,
  cvv: '',
  card_type: 'Unknown',
  bank_name: '',
  pool_type: 'public',
  status: 'available',
  max_use_count: 1,
  key_expire_time: '',
  notes: ''
})

// API 配置相关
const apiConfigs = ref<CardApiConfig[]>([])
const loadingConfigs = ref(false)
const showApiConfigDialog = ref(false)
const showAddConfigForm = ref(false)
const savingConfig = ref(false)
const editingConfig = ref<CardApiConfig | null>(null)

const configForm = reactive({
  name: '',
  redeem_url: '',
  query_url: '',
  request_method: 'POST',
  timeout: 30,
  request_headers_str: '',
  response_mapping_str: '',
  is_active: true,
  notes: ''
})

const fetchCards = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (poolFilter.value !== 'all') {
      params.pool_type = poolFilter.value
    }

    const response = await cardsApi.getCards(params)
    cards.value = response.results
    total.value = response.count
    
    // 检查当前用户权限，只有超级管理员可以看到所属者列
    const userStore = useUserStore()
    showOwnerColumn.value = userStore.user?.is_superuser || false
  } catch (error) {
    ElMessage.error('获取虚拟卡列表失败')
  } finally {
    loading.value = false
  }
}

const getStatusType = (status: string) => {
  const map: Record<string, any> = {
    available: 'success',
    in_use: 'warning', 
    used: 'info',
    invalid: 'danger',
    expired: 'danger'
  }
  return map[status] || 'info'
}

// 根据 key_expire_time 动态判断显示状态
const getDisplayStatus = (row: any): string => {
  // 如果 key_expire_time 存在且已过期，优先显示"已过期"
  if (row.key_expire_time && isExpired(row.key_expire_time)) {
    return '已过期'
  }
  // 否则使用后端返回的状态
  return row.status_display || row.status
}

const getDisplayStatusType = (row: any): string => {
  // 如果 key_expire_time 存在且已过期，显示红色
  if (row.key_expire_time && isExpired(row.key_expire_time)) {
    return 'danger'
  }
  return getStatusType(row.status)
}

const isExpired = (expireTime: string) => {
  if (!expireTime) return false
  return new Date(expireTime) < new Date()
}

const formatCountdown = (expireTime: string) => {
  if (!expireTime) return '-'
  const now = new Date().getTime()
  const expire = new Date(expireTime).getTime()
  const diff = expire - now
  
  if (diff <= 0) return '已过期'
  
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) return `${days}天${hours % 24}小时`
  if (hours > 0) return `${hours}小时${minutes % 60}分`
  return `${minutes}分钟`
}

const editCard = (card: any) => {
  editingCardId.value = card.id
  Object.assign(editForm, {
    card_number: card.card_number || '',
    card_holder: card.card_holder || '',
    expiry_month: card.expiry_month || 1,
    expiry_year: card.expiry_year || 2024,
    cvv: card.cvv || '',
    card_type: card.card_type || 'Unknown',
    bank_name: card.bank_name || '',
    pool_type: card.pool_type || 'public',
    status: card.status || 'available',
    max_use_count: card.max_use_count || 1,
    key_expire_time: card.key_expire_time || '',
    notes: card.notes || ''
  })
  showEditDialog.value = true
}

const handleUpdateCard = async () => {
  if (!editingCardId.value) return
  
  updating.value = true
  try {
    const data: any = {
      card_holder: editForm.card_holder,
      expiry_month: editForm.expiry_month,
      expiry_year: editForm.expiry_year,
      card_type: editForm.card_type,
      bank_name: editForm.bank_name,
      pool_type: editForm.pool_type,
      status: editForm.status,
      max_use_count: editForm.max_use_count,
      notes: editForm.notes
    }
    // 只有填写了卡号/CVV才传（后端可能不允许更新敏感信息）
    if (editForm.card_number) {
      data.card_number = editForm.card_number
    }
    if (editForm.cvv) {
      data.cvv = editForm.cvv
    }
    // 卡密过期时间：空字符串转为 null
    data.key_expire_time = editForm.key_expire_time.trim() || null
    
    await cardsApi.updateCard(editingCardId.value, data)
    ElMessage.success('更新成功')
    showEditDialog.value = false
    editingCardId.value = null
    fetchCards()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '更新失败')
  } finally {
    updating.value = false
  }
}

const deleteCard = async (card: any) => {
  try {
    await cardsApi.deleteCard(card.id)
    ElMessage.success('删除成功')
    fetchCards()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const handleAddCard = async () => {
  try {
    const data = {
      card_number: cardForm.card_number,
      card_holder: cardForm.card_holder,
      expiry_month: cardForm.expiry_month,
      expiry_year: cardForm.expiry_year,
      cvv: cardForm.cvv,
      pool_type: cardForm.pool_type,
      card_type: detectCardType(cardForm.card_number),
      balance: 0.00,
      max_use_count: 1
    }
    await cardsApi.createCard(data as any)
    ElMessage.success('添加成功')
    showDialog.value = false
    fetchCards()
    Object.assign(cardForm, {
      card_number: '',
      card_holder: '',
      expiry_month: 1,
      expiry_year: 2024,
      cvv: '',
      pool_type: 'public'
    })
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

// 识别卡类型
const detectCardType = (cardNumber: string): string => {
  const firstDigit = cardNumber.charAt(0)
  if (firstDigit === '4') return 'Visa'
  if (firstDigit === '5') return 'Master'
  if (firstDigit === '3') return 'American Express'
  if (firstDigit === '6') return 'Discover'
  return 'Unknown'
}

// 解析卡片文本
const parseCardsText = (text: string): any[] => {
  const lines = text.split('\n').filter(line => line.trim() && !line.trim().startsWith('#'))
  const cards: any[] = []
  
  for (const line of lines) {
    const sections = line
      .split('|')
      .map(part => part.trim())
      .filter(Boolean)

    const baseParts = (sections[0] || '').split(/\s+/).filter(Boolean)
    if (baseParts.length < 4) {
      continue
    }

    const [cardNumber, month, year, cvv, ...noteParts] = baseParts
    const expiryMonth = parseInt(month, 10)
    let fullYear = parseInt(year, 10)

    if (Number.isNaN(expiryMonth) || Number.isNaN(fullYear)) {
      continue
    }

    if (fullYear < 100) {
      fullYear = 2000 + fullYear
    }

    const cardHolder = sections[1] || ''
    const addressLine1 = sections[2] || ''
    const city = sections[3] || ''
    const state = sections[4] || ''
    const postalCode = sections[5] || ''
    const country = sections[6] || ''

    const billingAddress = addressLine1 || city || state || postalCode || country
      ? {
          address_line1: addressLine1,
          city,
          state,
          postal_code: postalCode,
          country
        }
      : undefined

    cards.push({
      card_number: cardNumber,
      card_holder: cardHolder,
      expiry_month: expiryMonth,
      expiry_year: fullYear,
      cvv,
      card_type: detectCardType(cardNumber),
      notes: noteParts.join(' '),
      billing_address: billingAddress
    })
  }
  
  return cards
}

const fillImportExample = () => {
  importForm.cardsText = importExampleMode.value === 'basic'
    ? [
        '4466164106155628 07 28 694',
        '5481087143137903 01 32 749'
      ].join('\n')
    : [
        '4466164106155628 07 28 694 | TOM LEE | 123 Main St | Los Angeles | CA | 90001 | US',
        '5481087143137903 01 32 749 | JANE DOE | 500 5th Ave | New York | NY | 10018 | US'
      ].join('\n')
}

// 批量导入
const handleImport = async () => {
  if (!importForm.cardsText.trim()) {
    ElMessage.warning('请输入卡片数据')
    return
  }
  
  importing.value = true
  importResult.value = null
  
  try {
    const cardsData = parseCardsText(importForm.cardsText)
    
    if (cardsData.length === 0) {
      ElMessage.warning('没有解析到有效的卡片数据')
      importing.value = false
      return
    }
    
    // 转换为API需要的格式
    const formattedCards = cardsData.map(card => ({
      card_number: card.card_number,
      card_holder: card.card_holder || undefined,
      expiry_month: card.expiry_month,
      expiry_year: card.expiry_year,
      cvv: card.cvv,
      card_type: card.card_type,
      notes: card.notes || undefined,
      billing_address: card.billing_address
    }))
    
    const response = await cardsApi.importCards({
      cards_data: formattedCards,
      pool_type: importForm.pool_type
    })
    
    // 统一处理响应格式，后端现在返回 { code, message, data: { success, failed, ... } }
    const result = (response as any).data || response
    const successCount = result.success || 0
    const totalCount = result.total || 0
    const failedCount = result.failed || 0
    
    importResult.value = {
      type: failedCount === 0 ? 'success' : 'warning',
      message: '导入完成',
      data: {
        total: totalCount,
        success: successCount,
        failed: failedCount,
        errors: result.errors || []
      }
    }
    
    ElMessage.success(`成功导入 ${successCount} 张卡片`)
    fetchCards()
    
    // 如果全部成功，清空输入
    if (failedCount === 0) {
      importForm.cardsText = ''
    }
  } catch (error: any) {
    importResult.value = {
      type: 'error',
      message: error.response?.data?.message || '导入失败',
      data: null
    }
    ElMessage.error('批量导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  fetchCards()
  loadApiConfigs()
})

watch(poolFilter, () => {
  currentPage.value = 1
  fetchCards()
})

watch([showRedeemDialog, showApiConfigDialog], ([redeemOpen, configOpen]) => {
  if (!redeemOpen && !configOpen) return
  loadApiConfigs()
})

const formatBillingAddress = (address: any): string => {
  if (!address || Object.keys(address).length === 0) return '-'
  const parts = [
    address.address_line1,
    address.city,
    address.state,
    address.postal_code,
    address.country
  ].filter(Boolean)
  return parts.join(', ') || '-'
}

const handleRedeem = async () => {
  if (!redeemForm.key_id.trim()) {
    ElMessage.warning('请输入卡密')
    return
  }
  
  redeeming.value = true
  redeemResult.value = null
  
  try {
    const response = await cardsApi.redeemCard({
      key_id: redeemForm.key_id.trim(),
      pool_type: redeemForm.pool_type,
      config_id: redeemForm.config_id
    })
    
    // axios 拦截器已解包，response 可能是 {code, data} 或直接是 data
    const cardData = response.data || response
    
    if (cardData && typeof cardData === 'object' && 'id' in cardData) {
      redeemResult.value = {
        type: 'success',
        message: '导入成功！卡片已添加到卡池',
        data: cardData
      }
      ElMessage.success('导入成功')
      fetchCards()
      redeemForm.key_id = ''
    } else {
      redeemResult.value = {
        type: 'error',
        message: (response as any).message || '导入失败',
        data: null
      }
      ElMessage.error((response as any).message || '导入失败')
    }
  } catch (error: any) {
    const errMsg = error.response?.data?.message || error.message || '导入失败'
    redeemResult.value = {
      type: 'error',
      message: errMsg,
      data: null
    }
    ElMessage.error(errMsg)
  } finally {
    redeeming.value = false
  }
}

// API 配置管理方法
const loadApiConfigs = async () => {
  loadingConfigs.value = true
  try {
    // 用 getApiConfigs 加载所有配置（包括未启用的），用于管理页面
    const response = await cardsApi.getApiConfigs()
    // response 是分页格式 {results: [...]} 或直接数组
    if (response.results) {
      apiConfigs.value = response.results
    } else if (Array.isArray(response)) {
      apiConfigs.value = response
    } else {
      apiConfigs.value = []
    }
  } catch (error: any) {
    console.error('加载 API 配置失败', error)
    ElMessage.error(error?.response?.data?.message || error?.message || '加载 API 配置失败')
  } finally {
    loadingConfigs.value = false
  }
}

const resetConfigForm = () => {
  Object.assign(configForm, {
    name: '',
    redeem_url: '',
    query_url: '',
    request_method: 'POST',
    timeout: 30,
    request_headers_str: '',
    response_mapping_str: '',
    is_active: true,
    notes: ''
  })
  editingConfig.value = null
}

const editApiConfig = (config: CardApiConfig) => {
  editingConfig.value = config
  Object.assign(configForm, {
    name: config.name,
    redeem_url: config.redeem_url,
    query_url: config.query_url || '',
    request_method: config.request_method || 'POST',
    timeout: config.timeout || 30,
    request_headers_str: config.request_headers ? JSON.stringify(config.request_headers, null, 2) : '',
    response_mapping_str: config.response_mapping ? JSON.stringify(config.response_mapping, null, 2) : '',
    is_active: config.is_active,
    notes: config.notes || ''
  })
  showAddConfigForm.value = true
}

const saveApiConfig = async () => {
  if (!configForm.name || (!configForm.redeem_url && !configForm.query_url)) {
    ElMessage.warning('请填写配置名称和至少一个接口 URL')
    return
  }
  
  savingConfig.value = true
  try {
    let requestHeaders = {}
    let responseMapping = {}
    
    if (configForm.request_headers_str.trim()) {
      try {
        requestHeaders = JSON.parse(configForm.request_headers_str)
      } catch {
        ElMessage.error('请求头 JSON 格式错误')
        savingConfig.value = false
        return
      }
    }
    
    if (configForm.response_mapping_str.trim()) {
      try {
        responseMapping = JSON.parse(configForm.response_mapping_str)
      } catch {
        ElMessage.error('响应映射 JSON 格式错误')
        savingConfig.value = false
        return
      }
    }
    
    const data = {
      name: configForm.name,
      redeem_url: configForm.redeem_url,
      query_url: configForm.query_url,
      request_method: configForm.request_method,
      timeout: configForm.timeout,
      request_headers: requestHeaders,
      response_mapping: responseMapping,
      is_active: configForm.is_active,
      notes: configForm.notes
    }
    
    if (editingConfig.value) {
      await cardsApi.updateApiConfig(editingConfig.value.id, data)
      ElMessage.success('更新成功')
    } else {
      await cardsApi.createApiConfig(data)
      ElMessage.success('添加成功')
    }
    
    showAddConfigForm.value = false
    resetConfigForm()
    loadApiConfigs()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    savingConfig.value = false
  }
}

const setDefaultConfig = async (config: CardApiConfig) => {
  try {
    await cardsApi.setDefaultApiConfig(config.id)
    ElMessage.success(`${config.name} 已设为默认`)
    loadApiConfigs()
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

const deleteApiConfig = async (config: CardApiConfig) => {
  try {
    await cardsApi.deleteApiConfig(config.id)
    ElMessage.success('删除成功')
    loadApiConfigs()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}
</script>
