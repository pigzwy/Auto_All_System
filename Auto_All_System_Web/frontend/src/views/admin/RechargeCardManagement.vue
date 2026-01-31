<template>
  <div class="space-y-6 p-5">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-foreground">🎫 充值卡密管理</h1>
      <div class="flex items-center gap-2">
        <Button variant="secondary" size="sm" class="gap-2" @click="handleExport" :disabled="exporting">
          <Download class="h-4 w-4" :class="{ 'animate-spin': exporting }" />
          批量导出
        </Button>
        <Button size="sm" class="gap-2" @click="showGenerateDialog = true">
          <Plus class="h-4 w-4" />
          批量生成卡密
        </Button>
      </div>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">状态</span>
            <Select v-model="filters.status" @update:modelValue="fetchCards">
              <SelectTrigger class="w-[140px]">
                <SelectValue placeholder="全部" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="unused">未使用</SelectItem>
                <SelectItem value="used">已使用</SelectItem>
                <SelectItem value="expired">已过期</SelectItem>
                <SelectItem value="disabled">已禁用</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">面值</span>
            <Select
              :model-value="filters.amount ? String(filters.amount) : 'all'"
              @update:modelValue="filters.amount = $event === 'all' ? null : Number($event); fetchCards()"
            >
              <SelectTrigger class="w-[140px]">
                <SelectValue placeholder="全部" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="10">¥10</SelectItem>
                <SelectItem value="50">¥50</SelectItem>
                <SelectItem value="100">¥100</SelectItem>
                <SelectItem value="500">¥500</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button variant="outline" size="sm" class="gap-2" @click="fetchCards">
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent class="p-0">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-20">ID</TableHead>
                <TableHead class="min-w-[240px]">卡密</TableHead>
                <TableHead class="w-24">面值</TableHead>
                <TableHead class="w-24">状态</TableHead>
                <TableHead class="min-w-[140px]">批次号</TableHead>
                <TableHead class="min-w-[120px]">使用者</TableHead>
                <TableHead class="min-w-[160px]">过期时间</TableHead>
                <TableHead class="min-w-[160px]">创建时间</TableHead>
                <TableHead class="w-[200px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="loading && cards.length === 0">
                <TableCell colspan="9" class="py-10 text-center">
                  <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                </TableCell>
              </TableRow>
              <TableRow v-else v-for="row in cards" :key="row.id" class="hover:bg-muted/20">
                <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>
                <TableCell>
                  <div class="flex items-center gap-2">
                    <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs font-bold text-primary">{{ row.card_code }}</code>
                    <Button variant="ghost" size="xs" class="h-6 w-6" @click="copyCardCode(row.card_code)">
                      <Copy class="h-3 w-3" />
                    </Button>
                  </div>
                </TableCell>
                <TableCell class="font-bold text-destructive">¥{{ row.amount }}</TableCell>
                <TableCell>
                  <Badge :variant="getStatusVariant(row.status)" class="rounded-full">
                    {{ getStatusText(row.status) }}
                  </Badge>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground truncate" :title="row.batch_no">{{ row.batch_no }}</TableCell>
                <TableCell class="text-xs">{{ row.used_by_username || '-' }}</TableCell>
                <TableCell class="text-xs text-muted-foreground">
                  <span v-if="row.expires_at">{{ formatDateTime(row.expires_at) }}</span>
                  <span v-else class="text-emerald-600">永久有效</span>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground">{{ formatDateTime(row.created_at) }}</TableCell>
                <TableCell class="text-right">
                  <div class="flex items-center justify-end gap-2">
                    <Button variant="outline" size="xs" @click="viewDetail(row)">详情</Button>
                    <Button
                      v-if="row.status === 'unused'"
                      variant="destructive"
                      size="xs"
                      @click="disableCard(row)"
                    >
                      禁用
                    </Button>
                    <Button
                      v-else-if="row.status === 'disabled'"
                      variant="default"
                      size="xs"
                      class="bg-emerald-600 hover:bg-emerald-700"
                      @click="enableCard(row)"
                    >
                      启用
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
              <TableRow v-if="!loading && cards.length === 0">
                <TableCell colspan="9" class="py-10 text-center text-sm text-muted-foreground">暂无数据</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div class="p-4 flex items-center justify-end gap-2" v-if="total > pageSize">
          <Button variant="outline" size="sm" :disabled="currentPage <= 1" @click="currentPage--; fetchCards()">上一页</Button>
          <div class="text-sm text-muted-foreground">
            第 <span class="font-medium text-foreground">{{ currentPage }}</span> 页
          </div>
          <Button variant="outline" size="sm" :disabled="cards.length < pageSize" @click="currentPage++; fetchCards()">下一页</Button>
        </div>
      </CardContent>
    </Card>

    <!-- 批量生成对话框 -->
    <Dialog v-model:open="showGenerateDialog">
      <DialogContent class="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>批量生成充值卡密</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">生成数量</label>
            <div class="flex items-center gap-2">
              <Input v-model.number="generateForm.count" type="number" :min="1" :max="1000" class="flex-1" />
              <span class="text-xs text-muted-foreground">最多1000张</span>
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">面值 (元)</label>
            <Input v-model.number="generateForm.amount" type="number" :min="1" :max="10000" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">卡密前缀</label>
            <Input v-model="generateForm.prefix" maxlength="10" placeholder="可选，如：VIP" />
            <p class="text-xs text-muted-foreground">示例：填写"VIP"，生成VIP-XXXX-XXXX-XXXX格式</p>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">有效天数</label>
            <Input v-model.number="generateForm.expires_days" type="number" :min="1" placeholder="留空=永久有效" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <textarea
              v-model="generateForm.notes"
              rows="2"
              class="min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="可选，如：2026年1月活动卡密"
            />
          </div>
        </div>
        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showGenerateDialog = false">取消</Button>
          <Button :disabled="generating" class="gap-2" @click="handleGenerate">
            <Loader2 v-if="generating" class="h-4 w-4 animate-spin" />
            生成
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Plus, Download, RefreshCw, Loader2, Copy } from 'lucide-vue-next'
import { paymentsApi } from '@/api/payments'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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

const loading = ref(false)
const generating = ref(false)
const exporting = ref(false)
const cards = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showGenerateDialog = ref(false)

const filters = reactive({
  status: 'all',
  amount: null as number | null
})

const generateForm = reactive({
  count: 10,
  amount: 100,
  prefix: '',
  expires_days: undefined as number | undefined,
  notes: ''
})

const fetchCards = async () => {
  loading.value = true
  try {
    const statusParam = filters.status === 'all' ? undefined : filters.status
    
    const response: any = await paymentsApi.getRechargeCards({
      page: currentPage.value,
      page_size: pageSize.value,
      status: statusParam,
      amount: filters.amount || undefined
    })
    
    console.log('卡密列表响应:', response)
    
    // DRF分页格式: {count, next, previous, results}
    if (response && typeof response === 'object') {
      if (response.results) {
        cards.value = response.results
        total.value = response.count || 0
      } else if (Array.isArray(response)) {
        // 如果直接返回数组
        cards.value = response
        total.value = response.length
      } else {
        cards.value = []
        total.value = 0
      }
    } else {
      cards.value = []
      total.value = 0
    }
  } catch (error) {
    console.error('获取卡密列表失败:', error)
    ElMessage.error('获取卡密列表失败')
  } finally {
    loading.value = false
  }
}

const handleGenerate = async () => {
  if (generateForm.count < 1 || generateForm.amount < 1) {
    ElMessage.warning('请填写正确的生成数量和面值')
    return
  }

  generating.value = true
  try {
    const response: any = await paymentsApi.batchCreateCards({
      count: generateForm.count,
      amount: generateForm.amount,
      prefix: generateForm.prefix || undefined,
      expires_days: generateForm.expires_days ?? undefined,
      notes: generateForm.notes || undefined
    })
    
    const message = response.message || `成功生成 ${generateForm.count} 张卡密`
    ElMessage.success(message)
    
    showGenerateDialog.value = false
    
    // 重置表单
    generateForm.count = 10
    generateForm.amount = 100
    generateForm.prefix = ''
    generateForm.expires_days = undefined
    generateForm.notes = ''
    
    // 刷新列表
    await fetchCards()
  } catch (error: any) {
    console.error('生成卡密失败:', error)
    ElMessage.error(error?.response?.data?.message || '生成卡密失败')
  } finally {
    generating.value = false
  }
}

const copyCardCode = (code: string) => {
  navigator.clipboard.writeText(code)
  ElMessage.success('卡密已复制到剪贴板')
}

const viewDetail = (_row: any) => {
  ElMessage.info('查看详情功能开发中')
}

const disableCard = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要禁用这张卡密吗？禁用后可以重新启用。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await paymentsApi.disableCard(row.id)
    ElMessage.success('卡密已禁用')
    await fetchCards()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('禁用失败:', error)
      ElMessage.error('禁用失败')
    }
  }
}

const enableCard = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要启用这张卡密吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'success'
    })
    
    await paymentsApi.enableCard(row.id)
    ElMessage.success('卡密已启用')
    await fetchCards()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('启用失败:', error)
      ElMessage.error('启用失败')
    }
  }
}

const getStatusVariant = (status: string) => {
  const map: Record<string, any> = {
    unused: 'default', // success equivalent usually default or secondary in some themes, or custom green
    used: 'secondary',
    expired: 'outline',
    disabled: 'destructive'
  }
  return map[status] || 'secondary'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    unused: '未使用',
    used: '已使用',
    expired: '已过期',
    disabled: '已禁用'
  }
  return map[status] || status
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const handleExport = async () => {
  try {
    await ElMessageBox.confirm(
      '将导出当前筛选条件下的所有卡密（最多10000张），是否继续？',
      '批量导出',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    exporting.value = true
    const statusParam = filters.status === 'all' ? undefined : filters.status
    const response: any = await paymentsApi.exportFilteredCards({
      status: statusParam,
      amount: filters.amount || undefined
    })
    
    if (response && response.data) {
      const { count, cards: exportedCards } = response.data
      
      // 生成CSV内容
      const headers = ['ID', '卡密', '面值', '状态', '批次号', '过期时间', '创建时间', '备注']
      const csvContent = [
        headers.join(','),
        ...exportedCards.map((card: any) => [
          card.id,
          card.card_code,
          card.amount,
          getStatusText(card.status),
          card.batch_no || '',
          card.expires_at ? formatDateTime(card.expires_at) : '永久有效',
          formatDateTime(card.created_at),
          (card.notes || '').replace(/,/g, '，') // 替换逗号避免CSV格式问题
        ].join(','))
      ].join('\n')
      
      // 添加BOM以支持中文
      const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      
      link.setAttribute('href', url)
      link.setAttribute('download', `充值卡密_${new Date().getTime()}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      ElMessage.success(`成功导出 ${count} 张卡密`)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('导出失败:', error)
      ElMessage.error(error?.response?.data?.message || '导出失败')
    }
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchCards()
})
</script>
