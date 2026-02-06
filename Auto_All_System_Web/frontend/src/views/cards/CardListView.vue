<template>
  <div class="space-y-6 p-5">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-foreground">虚拟卡管理</h1>
      <div class="flex items-center gap-2">
        <Button variant="success" size="sm" class="gap-2" @click="showCreateDialog = true">
          <Plus class="h-4 w-4" />
          添加虚拟卡
        </Button>
        <Button variant="secondary" size="sm" class="gap-2" @click="showImportDialog = true">
          <Upload class="h-4 w-4" />
          批量导入
        </Button>
      </div>
    </div>

    <Tabs v-model:modelValue="activeTab" class="w-full" @update:modelValue="handleTabChange">
      <TabsList>
          <TabsTrigger value="my">私有卡池</TabsTrigger>
          <TabsTrigger value="public">公共卡池</TabsTrigger>
      </TabsList>

      <TabsContent value="my" class="mt-4">
        <Card class="bg-card text-card-foreground shadow-sm">
          <CardContent class="p-0">
            <div class="overflow-x-auto rounded-xl border border-border bg-background/70 shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow class="bg-muted/40">
                    <TableHead class="w-20">ID</TableHead>
                    <TableHead class="min-w-[200px]">卡号</TableHead>
                    <TableHead class="w-32">持卡人</TableHead>
                    <TableHead class="w-24">有效期</TableHead>
                    <TableHead class="min-w-[180px]">卡类型/银行</TableHead>
                    <TableHead class="w-24">状态</TableHead>
                    <TableHead class="w-24">使用次数</TableHead>
                    <TableHead class="w-24">余额</TableHead>
                    <TableHead v-if="isAdmin" class="w-32">所有者</TableHead>
                    <TableHead class="w-20 text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-if="loading && myCards.length === 0">
                    <TableCell :colspan="isAdmin ? 10 : 9" class="py-10 text-center">
                      <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                        <Loader2 class="h-4 w-4 animate-spin" />
                        加载中...
                      </div>
                    </TableCell>
                  </TableRow>
                  <TableRow v-else v-for="row in myCards" :key="row.id" class="hover:bg-muted/30">
                    <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>
                    <TableCell class="font-mono font-medium">{{ row.masked_card_number }}</TableCell>
                    <TableCell>{{ row.card_holder || '-' }}</TableCell>
                    <TableCell class="text-muted-foreground text-xs">{{ String(row.expiry_month).padStart(2, '0') }}/{{ row.expiry_year }}</TableCell>
                    <TableCell>
                      <div class="flex items-center gap-2">
                        <Badge :variant="row.card_type === 'visa' ? 'default' : 'secondary'" class="rounded-full uppercase">
                          {{ row.card_type || 'Unknown' }}
                        </Badge>
                        <span class="text-xs text-muted-foreground truncate max-w-[100px]" :title="row.bank_name || ''">{{ row.bank_name || '' }}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge :variant="getCardStatusVariant(row.status)" class="rounded-full">
                        {{ getCardStatusText(row.status) }}
                      </Badge>
                    </TableCell>
                    <TableCell>{{ row.use_count }}</TableCell>
                    <TableCell>{{ row.balance ? `¥${row.balance}` : '-' }}</TableCell>
                    <TableCell v-if="isAdmin" class="text-xs">{{ row.owner_user_name || '-' }}</TableCell>
                    <TableCell class="text-right">
                      <Button variant="ghost" size="xs" class="text-destructive hover:text-destructive h-auto p-0" @click="handleDeleteCard(row)">删除</Button>
                    </TableCell>
                  </TableRow>
                  <TableRow v-if="!loading && myCards.length === 0">
                    <TableCell :colspan="isAdmin ? 10 : 9" class="py-10 text-center text-sm text-muted-foreground">暂无虚拟卡</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="public" class="mt-4">
        <Card class="bg-card text-card-foreground shadow-sm">
          <CardContent class="p-0">
            <div class="overflow-x-auto rounded-xl border border-border bg-background/70 shadow-sm">
              <Table>
                <TableHeader>
                  <TableRow class="bg-muted/40">
                    <TableHead class="w-20">ID</TableHead>
                    <TableHead class="min-w-[180px]">卡类型/银行</TableHead>
                    <TableHead class="w-24">状态</TableHead>
                    <TableHead class="w-32">已用/最大</TableHead>
                    <TableHead class="w-24">余额</TableHead>
                    <TableHead v-if="isAdmin" class="w-32">所有者</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-if="loading && publicCards.length === 0">
                    <TableCell :colspan="isAdmin ? 6 : 5" class="py-10 text-center">
                      <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                        <Loader2 class="h-4 w-4 animate-spin" />
                        加载中...
                      </div>
                    </TableCell>
                  </TableRow>
                  <TableRow v-else v-for="row in publicCards" :key="row.id" class="hover:bg-muted/30">
                    <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>
                    <TableCell>
                      <div class="flex items-center gap-2">
                        <Badge :variant="row.card_type === 'visa' ? 'default' : 'secondary'" class="rounded-full uppercase">
                          {{ row.card_type || 'Unknown' }}
                        </Badge>
                        <span class="text-xs text-muted-foreground truncate max-w-[100px]" :title="row.bank_name || ''">{{ row.bank_name || '' }}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge :variant="getCardStatusVariant(row.status)" class="rounded-full">
                        {{ getCardStatusText(row.status) }}
                      </Badge>
                    </TableCell>
                    <TableCell class="text-xs text-muted-foreground">{{ row.use_count }} / {{ row.max_use_count || '∞' }}</TableCell>
                    <TableCell>{{ row.balance ? `¥${row.balance}` : '-' }}</TableCell>
                    <TableCell v-if="isAdmin" class="text-xs">{{ row.owner_user_name || '-' }}</TableCell>
                  </TableRow>
                  <TableRow v-if="!loading && publicCards.length === 0">
                    <TableCell :colspan="isAdmin ? 6 : 5" class="py-10 text-center text-sm text-muted-foreground">暂无公共卡</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>

    <!-- 添加虚拟卡对话框 -->
    <Dialog v-model:open="showCreateDialog">
      <DialogContent class="sm:max-w-[500px] bg-card/95">
        <DialogHeader>
          <DialogTitle>添加虚拟卡</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">卡号</label>
            <Input v-model="createForm.card_number" placeholder="请输入卡号" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">有效期</label>
            <div class="flex items-center gap-2">
              <Input v-model="createForm.exp_month" placeholder="月 (MM)" class="flex-1" />
              <span class="text-muted-foreground">/</span>
              <Input v-model="createForm.exp_year" placeholder="年 (YY)" class="flex-1" />
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">CVV</label>
            <Input v-model="createForm.cvv" placeholder="请输入CVV" maxlength="4" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">卡类型</label>
            <Select v-model="createForm.card_type">
              <SelectTrigger>
                <SelectValue placeholder="请选择卡类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="visa">Visa</SelectItem>
                <SelectItem value="mastercard">MasterCard</SelectItem>
                <SelectItem value="amex">American Express</SelectItem>
                <SelectItem value="other">其他</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">银行名称</label>
            <Input v-model="createForm.bank_name" placeholder="选填" />
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">是否公开</label>
            <Switch :checked="createForm.is_public" @update:checked="createForm.is_public = $event" />
          </div>
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">可重复使用</label>
            <Switch :checked="createForm.can_reuse" @update:checked="createForm.can_reuse = $event" />
          </div>
          <div v-if="createForm.can_reuse" class="grid gap-2">
            <label class="text-sm font-medium">最大使用次数</label>
            <Input v-model="createForm.max_uses" type="number" min="1" placeholder="不限制留空" />
          </div>
        </div>
        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showCreateDialog = false">取消</Button>
          <Button :disabled="creating" class="gap-2" @click="handleCreateCard">
            <Loader2 v-if="creating" class="h-4 w-4 animate-spin" />
            添加
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 批量导入对话框 -->
    <Dialog v-model:open="showImportDialog">
      <DialogContent class="sm:max-w-[700px] bg-card/95">
        <DialogHeader>
          <DialogTitle>批量导入虚拟卡</DialogTitle>
        </DialogHeader>
        
        <Alert class="mb-2">
          <AlertTitle>格式说明</AlertTitle>
          <AlertDescription>
            <div class="space-y-1 text-sm">
              <div>基础格式：<code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">卡号 月份 年份 CVV</code>（空格分隔）</div>
              <div>扩展格式：<code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">卡号 月份 年份 CVV | 持卡人 | 地址1 | 城市 | 州 | 邮编 | 国家</code></div>
              <div>示例：<code class="rounded bg-muted px-1.5 py-0.5 font-mono text-primary">4466164106155628 07 28 694 | TOM LEE | 123 Main St | Los Angeles | CA | 90001 | US</code></div>
              <div class="text-xs text-muted-foreground">💡 4开头自动识别为Visa，5开头自动识别为Master</div>
            </div>
          </AlertDescription>
        </Alert>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">卡片数据</label>
            <Textarea
              v-model="importForm.cardsText"
              rows="10"
              class="min-h-[200px] font-mono text-sm"
              placeholder="粘贴卡片数据，每行一张卡&#10;4466164106155628 07 28 694&#10;4466164106155628 07 28 694 | TOM LEE | 123 Main St | Los Angeles | CA | 90001 | US"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">卡池类型</label>
            <RadioGroup v-model="importForm.pool_type" class="flex gap-4">
              <div class="flex items-center space-x-2">
                <RadioGroupItem id="r-public" value="public" />
                <Label for="r-public">公共卡池</Label>
              </div>
              <div class="flex items-center space-x-2">
                <RadioGroupItem id="r-private" value="private" />
                <Label for="r-private">私有卡池</Label>
              </div>
            </RadioGroup>
          </div>
        </div>

        <div v-if="importResult" class="mt-2 rounded-md border p-4" :class="importResult.type === 'error' ? 'border-destructive/50 bg-destructive/10 text-destructive' : 'border-emerald-500/50 bg-emerald-500/10 text-emerald-700'">
          <div class="font-medium">{{ importResult.message }}</div>
          <div v-if="importResult.errors && importResult.errors.length > 0" class="mt-2 text-xs opacity-90 max-h-32 overflow-y-auto">
            <div v-for="(error, index) in importResult.errors" :key="index">
              {{ error }}
            </div>
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showImportDialog = false">取消</Button>
          <Button :disabled="importing" class="gap-2" @click="handleImportCards">
            <Loader2 v-if="importing" class="h-4 w-4 animate-spin" />
            导入
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Plus, Upload, Loader2 } from 'lucide-vue-next'
import { cardsApi } from '@/api/cards'
import { useUserStore } from '@/stores/user'
import type { Card as CardModel, CardCreateForm } from '@/types'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.user?.is_staff || userStore.user?.is_superuser)

const loading = ref(false)
const creating = ref(false)
const importing = ref(false)
const activeTab = ref('my')
const showCreateDialog = ref(false)
const showImportDialog = ref(false)
const myCards = ref<CardModel[]>([])
const publicCards = ref<CardModel[]>([])

const createForm = reactive({
  card_number: '',
  exp_month: '',
  exp_year: '',
  cvv: '',
  card_type: 'visa',
  bank_name: '',
  is_public: false,
  can_reuse: false,
  max_uses: undefined
})

const importForm = reactive({
  cardsText: '',
  pool_type: 'private'
})

const importResult = ref<{ type: string; message: string; errors?: string[] } | null>(null)

const fetchMyCards = async () => {
  loading.value = true
  try {
    const response = await cardsApi.getMyCards() as any
    myCards.value = Array.isArray(response) ? response : (response.cards || [])
  } catch (error) {
    console.error('Failed to fetch my cards:', error)
  } finally {
    loading.value = false
  }
}

const fetchPublicCards = async () => {
  loading.value = true
  try {
    const response = await cardsApi.getAvailableCards({ pool_type: 'public' }) as any
    if (Array.isArray(response)) {
      publicCards.value = response
    } else if (Array.isArray(response?.data)) {
      publicCards.value = response.data
    } else if (Array.isArray(response?.results)) {
      publicCards.value = response.results
    } else {
      publicCards.value = []
    }
  } catch (error) {
    console.error('Failed to fetch public cards:', error)
  } finally {
    loading.value = false
  }
}

const handleTabChange = (val: string | number) => {
  const tab = String(val)
  if (tab === 'my') {
    fetchMyCards()
  } else {
    fetchPublicCards()
  }
}

const handleCreateCard = async () => {
  if (!createForm.card_number || !createForm.exp_month || !createForm.exp_year || !createForm.cvv) {
    ElMessage.warning('请填写完整信息')
    return
  }

  creating.value = true
  try {
    const cardData: CardCreateForm = {
      card_number: createForm.card_number,
      expiry_month: parseInt(createForm.exp_month),
      expiry_year: parseInt(createForm.exp_year),
      cvv: createForm.cvv,
      card_type: createForm.card_type,
      pool_type: createForm.is_public ? 'public' : 'private'
    }
    await cardsApi.createCard(cardData)
    ElMessage.success('虚拟卡添加成功')
    showCreateDialog.value = false
    if (activeTab.value === 'my') {
      fetchMyCards()
    }
  } catch (error) {
    console.error('Failed to create card:', error)
  } finally {
    creating.value = false
  }
}

const handleDeleteCard = async (card: CardModel) => {
  try {
    await ElMessageBox.confirm('确定要删除此虚拟卡吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await cardsApi.deleteCard(card.id)
    ElMessage.success('虚拟卡已删除')
    fetchMyCards()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete card:', error)
    }
  }
}

const handleImportCards = async () => {
  if (!importForm.cardsText.trim()) {
    ElMessage.warning('请输入卡片数据')
    return
  }

  importResult.value = null
  importing.value = true

  try {
    const lines = importForm.cardsText.trim().split('\n').filter(line => line.trim())
    const cardsData: any[] = []
    const errors: string[] = []

    lines.forEach((line, index) => {
      const sections = line
        .split('|')
        .map(part => part.trim())
        .filter(Boolean)

      const parts = (sections[0] || '').split(/\s+/).filter(Boolean)
      if (parts.length < 4) {
        errors.push(`第 ${index + 1} 行格式不正确: ${line}`)
        return
      }

      const [cardNumber, expMonth, expYear, cvv] = parts
      const cardHolder = sections[1] || ''
      const addressLine1 = sections[2] || ''
      const city = sections[3] || ''
      const state = sections[4] || ''
      const postalCode = sections[5] || ''
      const country = sections[6] || ''

      let cardType = 'other'
      if (cardNumber.startsWith('4')) {
        cardType = 'visa'
      } else if (cardNumber.startsWith('5')) {
        cardType = 'mastercard'
      }

      const billingAddress = (addressLine1 || city || state || postalCode || country)
        ? {
            address_line1: addressLine1,
            city,
            state,
            postal_code: postalCode,
            country
          }
        : undefined

      cardsData.push({
        card_number: cardNumber,
        expiry_month: parseInt(expMonth),
        expiry_year: parseInt(expYear),
        cvv: cvv,
        card_type: cardType,
        card_holder: cardHolder || undefined,
        notes: parts.slice(4).join(' ') || undefined,
        billing_address: billingAddress
      })
    })

    if (errors.length > 0) {
      importResult.value = {
        type: 'error',
        message: '导入失败',
        errors
      }
      return
    }

    const response = await cardsApi.importCards({
      cards_data: cardsData,
      pool_type: importForm.pool_type
    })

    const result = (response as any).data || response
    
    importResult.value = {
      type: 'success',
      message: `成功导入 ${result.success} 张卡片，失败 ${result.failed} 张`,
      errors: result.errors?.map((e: any) => `卡号 ${e.card_number}: ${e.error}`) || []
    }

    if (result.success > 0) {
      if (activeTab.value === 'public') {
        fetchPublicCards()
      } else {
        fetchMyCards()
      }
      importForm.cardsText = ''
    }
  } catch (error: any) {
    importResult.value = {
      type: 'error',
      message: '导入请求失败: ' + (error.message || '未知错误')
    }
  } finally {
    importing.value = false
  }
}

const getCardStatusVariant = (status: string) => {
  const map: Record<string, any> = {
    available: 'default', // success equivalent usually default or secondary in some themes, or custom green
    in_use: 'secondary',
    used: 'secondary',
    invalid: 'destructive',
    expired: 'outline'
  }
  // Shadcn badge variants: default, secondary, destructive, outline
  // If we want green, we might need custom class. 'default' is usually primary color (black/dark).
  // Let's use available variants.
  return map[status] || 'outline'
}

const getCardStatusText = (status: string) => {
  const map: Record<string, string> = {
    available: '可用',
    in_use: '使用中',
    used: '已使用',
    invalid: '无效',
    expired: '已过期'
  }
  return map[status] || status
}

onMounted(() => {
  fetchMyCards()
})
</script>
