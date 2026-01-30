<template>
  <div class="card-management">
    <div class="page-header">
      <h1>虚拟卡管理</h1>
      <el-button-group>
        <el-button type="primary" @click="showDialog = true">
          <el-icon><Plus /></el-icon>
          添加虚拟卡
        </el-button>
        <el-button type="success" @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>
          批量导入
        </el-button>
        <el-button type="warning" @click="showRedeemDialog = true">
          <el-icon><Key /></el-icon>
          卡密激活
        </el-button>
      </el-button-group>
    </div>

    <el-card shadow="hover">
      <el-table :data="cards" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="卡号" width="200">
          <template #default="{ row }">
            <span class="font-mono">
              {{ row.card_number || row.masked_card_number }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="card_holder" label="持卡人" width="150">
          <template #default="{ row }">
            {{ row.card_holder || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="有效期" width="100">
          <template #default="{ row }">
            {{ String(row.expiry_month).padStart(2, '0') }}/{{ row.expiry_year }}
          </template>
        </el-table-column>
        <el-table-column label="卡类型/银行" width="180">
          <template #default="{ row }">
            <div class="flex items-center gap-2">
              <el-tag size="small" :type="row.card_type === 'visa' ? 'primary' : 'warning'">
                {{ row.card_type || 'Unknown' }}
              </el-tag>
              <span class="text-xs text-gray-500">{{ row.bank_name || '' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.pool_type === 'public' ? 'primary' : 'success'">
              {{ row.pool_type_display || (row.pool_type === 'public' ? '公共' : '私有') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status_display || row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="剩余时间" width="120">
          <template #default="{ row }">
            <template v-if="row.key_expire_time">
              <span v-if="isExpired(row.key_expire_time)" class="text-red-500">已过期</span>
              <span v-else class="text-green-600">{{ formatCountdown(row.key_expire_time) }}</span>
            </template>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column label="使用次数" width="120">
          <template #default="{ row }">
            <span>{{ row.use_count }}</span>
            <span class="text-gray-400"> / {{ row.max_use_count || '∞' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="账单地址" min-width="200">
          <template #default="{ row }">
            <div v-if="row.billing_address && Object.keys(row.billing_address).length > 0" class="text-xs">
              <div>{{ row.billing_address.address_line1 || '-' }}</div>
              <div class="text-gray-500">
                {{ [row.billing_address.city, row.billing_address.state, row.billing_address.postal_code].filter(Boolean).join(', ') }}
              </div>
              <div class="text-gray-400">{{ row.billing_address.country || '' }}</div>
            </div>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column v-if="showOwnerColumn" label="所属者" width="120">
          <template #default="{ row }">
            <span v-if="row.owner_user">
              {{ row.owner_user_name || `用户${row.owner_user}` }}
            </span>
            <span v-else class="text-gray">公共卡池</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <div class="operation-buttons">
              <el-button link type="primary" @click="editCard(row)">编辑</el-button>
              <el-button link type="danger" @click="deleteCard(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchCards"
      />
    </el-card>

    <!-- 添加对话框 -->
    <el-dialog v-model="showDialog" title="添加虚拟卡" width="500px">
      <el-form :model="cardForm" label-width="100px">
        <el-form-item label="卡号">
          <el-input v-model="cardForm.card_number" placeholder="16位卡号" />
        </el-form-item>
        <el-form-item label="持卡人">
          <el-input v-model="cardForm.card_holder" placeholder="持卡人姓名" />
        </el-form-item>
        <el-form-item label="过期月份">
          <el-input-number v-model="cardForm.expiry_month" :min="1" :max="12" />
        </el-form-item>
        <el-form-item label="过期年份">
          <el-input-number v-model="cardForm.expiry_year" :min="2024" :max="2099" />
        </el-form-item>
        <el-form-item label="CVV">
          <el-input v-model="cardForm.cvv" placeholder="3-4位安全码" maxlength="4" />
        </el-form-item>
        <el-form-item label="卡池类型">
          <el-radio-group v-model="cardForm.pool_type">
            <el-radio label="public">公共卡池</el-radio>
            <el-radio label="private">私有卡池</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddCard">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showImportDialog" title="批量导入虚拟卡" width="700px">
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        <template #title>
          <div>格式说明：每行一张卡，格式为 <code>卡号 月份 年份 CVV</code>（空格分隔）</div>
          <div style="margin-top: 8px">示例：<code>4466164106155628 07 28 694</code></div>
          <div style="margin-top: 4px; font-size: 12px">💡 4开头自动识别为Visa，5开头自动识别为Master</div>
        </template>
      </el-alert>
      
      <el-form :model="importForm" label-width="100px">
        <el-form-item label="卡片数据">
          <el-input
            v-model="importForm.cardsText"
            type="textarea"
            :rows="10"
            placeholder="粘贴卡片数据，每行一张卡&#10;4466164106155628 07 28 694&#10;5481087143137903 01 32 749"
          />
        </el-form-item>
        <el-form-item label="卡池类型">
          <el-radio-group v-model="importForm.pool_type">
            <el-radio label="public">公共卡池</el-radio>
            <el-radio label="private">私有卡池</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      
      <div v-if="importResult" class="import-result">
        <el-alert :type="importResult.type" :closable="false">
          <template #title>
            <div>{{ importResult.message }}</div>
            <div v-if="importResult.data" style="margin-top: 8px; font-size: 14px">
              总数：{{ importResult.data.total }} | 
              成功：{{ importResult.data.success }} | 
              失败：{{ importResult.data.failed }}
            </div>
          </template>
        </el-alert>
        <div v-if="importResult.data?.errors?.length" style="margin-top: 12px">
          <el-collapse>
            <el-collapse-item title="查看错误详情" name="errors">
              <div v-for="(error, index) in importResult.data.errors" :key="index" class="error-item">
                <span>卡号: {{ error.card_number }}</span>
                <span style="color: #f56c6c">错误: {{ error.error }}</span>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing">
          {{ importing ? '导入中...' : '开始导入' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 卡密激活对话框 -->
    <el-dialog v-model="showRedeemDialog" title="卡密激活" width="500px" @open="loadApiConfigs">
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        <template #title>
          <div>输入卡密后将调用激活接口获取完整卡信息（包含账单地址）</div>
        </template>
      </el-alert>
      
      <el-form :model="redeemForm" label-width="100px">
        <el-form-item label="API 配置">
          <el-select 
            v-model="redeemForm.config_id" 
            placeholder="选择 API 配置（默认使用系统默认）"
            clearable
            style="width: 100%"
          >
            <el-option 
              v-for="config in apiConfigs" 
              :key="config.id" 
              :label="config.name + (config.is_default ? ' (默认)' : '')" 
              :value="config.id"
            />
          </el-select>
          <div class="text-xs text-gray-400 mt-1">
            <el-link type="primary" @click="showApiConfigDialog = true">管理 API 配置</el-link>
          </div>
        </el-form-item>
        <el-form-item label="卡密">
          <el-input 
            v-model="redeemForm.key_id" 
            placeholder="输入卡密 key_id"
            clearable
          />
        </el-form-item>
        <el-form-item label="卡池类型">
          <el-radio-group v-model="redeemForm.pool_type">
            <el-radio label="public">公共卡池</el-radio>
            <el-radio label="private">私有卡池</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      
      <div v-if="redeemResult" class="redeem-result">
        <el-alert :type="redeemResult.type" :closable="false">
          <template #title>
            <div>{{ redeemResult.message }}</div>
          </template>
        </el-alert>
        <div v-if="redeemResult.data" class="card-info-preview">
          <el-descriptions :column="2" border size="small" style="margin-top: 12px">
            <el-descriptions-item label="卡号">{{ redeemResult.data.masked_card_number }}</el-descriptions-item>
            <el-descriptions-item label="有效期">{{ String(redeemResult.data.expiry_month).padStart(2, '0') }}/{{ redeemResult.data.expiry_year }}</el-descriptions-item>
            <el-descriptions-item label="持卡人">{{ redeemResult.data.card_holder || '-' }}</el-descriptions-item>
            <el-descriptions-item label="卡类型">{{ redeemResult.data.card_type }}</el-descriptions-item>
            <el-descriptions-item label="地址" :span="2">
              {{ formatBillingAddress(redeemResult.data.billing_address) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="showRedeemDialog = false">关闭</el-button>
        <el-button type="primary" @click="handleRedeem" :loading="redeeming">
          {{ redeeming ? '激活中...' : '激活' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- API 配置管理对话框 -->
    <el-dialog v-model="showApiConfigDialog" title="API 配置管理" width="800px">
      <div class="mb-4">
        <el-button type="primary" size="small" @click="resetConfigForm(); showAddConfigForm = true">
          添加配置
        </el-button>
      </div>
      
      <el-table :data="apiConfigs" v-loading="loadingConfigs" stripe size="small">
        <el-table-column prop="name" label="名称" width="120">
          <template #default="{ row }">
            {{ row.name }}
            <el-tag v-if="row.is_default" size="small" type="success" class="ml-1">默认</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="redeem_url" label="激活接口" min-width="200">
          <template #default="{ row }">
            <span class="text-xs font-mono">{{ row.redeem_url }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editApiConfig(row)">编辑</el-button>
            <el-button link type="success" size="small" v-if="!row.is_default" @click="setDefaultConfig(row)">设为默认</el-button>
            <el-button link type="danger" size="small" @click="deleteApiConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 添加/编辑配置表单 -->
      <el-dialog v-model="showAddConfigForm" :title="editingConfig ? '编辑配置' : '添加配置'" width="600px" append-to-body>
        <el-form :model="configForm" label-width="120px">
          <el-form-item label="配置名称" required>
            <el-input v-model="configForm.name" placeholder="如: ActCard" />
          </el-form-item>
          <el-form-item label="激活接口 URL" required>
            <el-input v-model="configForm.redeem_url" placeholder="https://actcard.xyz/api/keys/redeem" />
          </el-form-item>
          <el-form-item label="查询接口 URL">
            <el-input v-model="configForm.query_url" placeholder="https://actcard.xyz/api/keys/query" />
          </el-form-item>
          <el-form-item label="请求方法">
            <el-select v-model="configForm.request_method" style="width: 120px">
              <el-option label="POST" value="POST" />
              <el-option label="GET" value="GET" />
            </el-select>
          </el-form-item>
          <el-form-item label="超时时间(秒)">
            <el-input-number v-model="configForm.timeout" :min="5" :max="120" />
          </el-form-item>
          <el-form-item label="请求头 (JSON)">
            <el-input 
              v-model="configForm.request_headers_str" 
              type="textarea" 
              :rows="2"
              placeholder='{"Authorization": "Bearer xxx"}'
            />
          </el-form-item>
          <el-form-item label="响应映射 (JSON)">
            <el-input 
              v-model="configForm.response_mapping_str" 
              type="textarea" 
              :rows="3"
              placeholder='{"data_path": "checkout", "fields": {"card_number": "card_number"}}'
            />
            <div class="text-xs text-gray-400 mt-1">
              data_path: 响应中卡数据的路径；fields: 字段名映射
            </div>
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="configForm.is_active" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="configForm.notes" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showAddConfigForm = false">取消</el-button>
          <el-button type="primary" @click="saveApiConfig" :loading="savingConfig">保存</el-button>
        </template>
      </el-dialog>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { cardsApi } from '@/api/cards'
import type { CardApiConfig } from '@/api/cards'
import { ElMessage } from 'element-plus'
import { Plus, Upload, Key } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import type { Card } from '@/types'

const loading = ref(false)
const cards = ref<Card[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showDialog = ref(false)
const showImportDialog = ref(false)
const showRedeemDialog = ref(false)
const importing = ref(false)
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

const redeemForm = reactive({
  key_id: '',
  pool_type: 'public',
  config_id: undefined as number | undefined
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
    const response = await cardsApi.getCards({
      page: currentPage.value,
      page_size: pageSize.value
    })
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

const editCard = (_card: any) => {
  ElMessage.info('编辑功能开发中')
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
    const parts = line.trim().split(/\s+/)
    if (parts.length === 4) {
      const [cardNumber, month, year, cvv] = parts
      const cardType = detectCardType(cardNumber)
      
      // 年份处理：如果是两位数，加2000
      let fullYear = parseInt(year)
      if (fullYear < 100) {
        fullYear = 2000 + fullYear
      }
      
      cards.push({
        card_number: cardNumber,
        card_holder: cardType, // 使用卡类型作为持卡人
        expiry_month: parseInt(month),
        expiry_year: fullYear,
        cvv: cvv
      })
    }
  }
  
  return cards
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
      card_holder: card.card_holder,
      expiry_month: card.expiry_month,
      expiry_year: card.expiry_year,
      cvv: card.cvv
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
    
    if (cardData && cardData.id) {
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
  } catch (error) {
    console.error('加载 API 配置失败', error)
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

<style scoped lang="scss">
.card-management {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    h1 {
      margin: 0;
    }
  }

  .operation-buttons {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .font-mono {
    font-family: 'Courier New', Courier, monospace;
    font-weight: 500;
  }

  .el-pagination {
    margin-top: 20px;
    justify-content: center;
  }
  
  .import-result {
    margin-top: 16px;
    
    .error-item {
      padding: 8px;
      border-bottom: 1px solid #ebeef5;
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      
      &:last-child {
        border-bottom: none;
      }
    }
  }
  
  code {
    background: #f5f7fa;
    padding: 2px 6px;
    border-radius: 3px;
    color: #409eff;
    font-family: 'Courier New', monospace;
  }
  
  .text-gray {
    color: #909399;
    font-size: 12px;
  }
  
  .redeem-result {
    margin-top: 16px;
  }
  
  .card-info-preview {
    margin-top: 12px;
  }
}
</style>
