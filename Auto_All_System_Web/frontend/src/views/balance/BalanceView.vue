<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-foreground">余额管理</h1>
    </div>

    <!-- 余额卡片 -->
    <div class="grid gap-6 md:grid-cols-2">
      <Card class="bg-card text-card-foreground">
        <CardHeader>
          <CardTitle>账户余额</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="flex flex-col items-center py-4">
            <div class="mb-4 text-4xl font-bold text-primary">¥{{ balance?.balance || '0.00' }}</div>
            <Button size="lg" class="gap-2" @click="goToRecharge">
              <Plus class="h-4 w-4" />
              充值
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card class="bg-card text-card-foreground">
        <CardHeader>
          <CardTitle>冻结余额</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="flex flex-col items-center py-4">
            <div class="mb-2 text-4xl font-bold text-muted-foreground">¥{{ balance?.frozen_balance || '0.00' }}</div>
            <div class="text-sm text-muted-foreground">正在执行中的任务所占用的余额</div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 交易记录 -->
    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <div class="flex items-center justify-between">
          <CardTitle>交易记录</CardTitle>
          <Button variant="outline" size="sm" class="gap-2" @click="fetchTransactions">
            <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div class="mb-4 flex items-center gap-2">
          <span class="text-sm font-medium">交易类型</span>
          <Select v-model="filters.transaction_type" @update:modelValue="fetchTransactions">
            <SelectTrigger class="w-[180px]">
              <SelectValue placeholder="全部" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部</SelectItem>
              <SelectItem value="recharge">充值</SelectItem>
              <SelectItem value="consume">消费</SelectItem>
              <SelectItem value="refund">退款</SelectItem>
              <SelectItem value="freeze">冻结</SelectItem>
              <SelectItem value="unfreeze">解冻</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-20">ID</TableHead>
                <TableHead class="w-24">类型</TableHead>
                <TableHead class="w-32">金额</TableHead>
                <TableHead class="w-32">余额</TableHead>
                <TableHead class="min-w-[200px]">说明</TableHead>
                <TableHead class="w-40 text-right">时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="loading && transactions.length === 0">
                <TableCell colspan="6" class="py-10 text-center">
                  <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                </TableCell>
              </TableRow>
              <TableRow v-else v-for="row in transactions" :key="row.id">
                <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>
                <TableCell>
                  <Badge :variant="getTransactionVariant(row.transaction_type)" class="rounded-full">
                    {{ getTransactionText(row.transaction_type) }}
                  </Badge>
                </TableCell>
                <TableCell>
                  <span :class="getAmountClass(row.transaction_type)">
                    {{ formatAmount(row.amount, row.transaction_type) }}
                  </span>
                </TableCell>
                <TableCell>¥{{ row.balance_after }}</TableCell>
                <TableCell class="text-muted-foreground">{{ row.description }}</TableCell>
                <TableCell class="text-right text-muted-foreground">{{ formatDate(row.created_at) }}</TableCell>
              </TableRow>
              <TableRow v-if="!loading && transactions.length === 0">
                <TableCell colspan="6" class="py-10 text-center text-sm text-muted-foreground">暂无交易记录</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div class="mt-4 flex items-center justify-end gap-2" v-if="total > pageSize">
          <Button variant="outline" size="sm" :disabled="currentPage <= 1" @click="currentPage--; fetchTransactions()">上一页</Button>
          <div class="text-sm text-muted-foreground">
            第 <span class="font-medium text-foreground">{{ currentPage }}</span> 页
          </div>
          <Button variant="outline" size="sm" :disabled="transactions.length < pageSize" @click="currentPage++; fetchTransactions()">下一页</Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { balanceApi, type BalanceLog } from '@/api/balance'
import type { UserBalance } from '@/types'
import dayjs from 'dayjs'
import { Plus, RefreshCw, Loader2 } from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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

const router = useRouter()
const loading = ref(false)
const balance = ref<UserBalance | null>(null)
const transactions = ref<BalanceLog[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const filters = reactive({
  transaction_type: 'all'
})

const fetchBalance = async () => {
  try {
    balance.value = await balanceApi.getMyBalance()
  } catch (error) {
    console.error('Failed to fetch balance:', error)
  }
}

const fetchTransactions = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (filters.transaction_type && filters.transaction_type !== 'all') {
      params.transaction_type = filters.transaction_type
    }
    const response = await balanceApi.getBalanceLogs(params)
    transactions.value = response.results
    total.value = response.count
  } catch (error) {
    console.error('Failed to fetch transactions:', error)
  } finally {
    loading.value = false
  }
}

const goToRecharge = () => {
  router.push({ name: 'Recharge' })
}

const getTransactionVariant = (type: string) => {
  const map: Record<string, any> = {
    recharge: 'default',
    consume: 'secondary',
    refund: 'default',
    freeze: 'outline',
    unfreeze: 'outline'
  }
  return map[type] || 'secondary'
}

const getTransactionText = (type: string) => {
  const map: Record<string, string> = {
    recharge: '充值',
    consume: '消费',
    refund: '退款',
    freeze: '冻结',
    unfreeze: '解冻'
  }
  return map[type] || type
}

const getAmountClass = (type: string) => {
  return (type === 'recharge' || type === 'refund') ? 'text-emerald-600 font-bold' : 'text-foreground'
}

const formatAmount = (amount: string, type: string) => {
  const prefix = (type === 'recharge' || type === 'refund') ? '+' : '-'
  return `${prefix}¥${amount}`
}

const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchBalance()
  fetchTransactions()
})
</script>
