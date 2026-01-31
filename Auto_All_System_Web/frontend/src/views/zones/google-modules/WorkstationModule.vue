<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h2 class="text-2xl font-semibold text-foreground">工作台</h2>
        <p class="mt-1 text-sm text-muted-foreground">概览与最近任务</p>
      </div>
      <Button variant="outline" size="sm" class="gap-2" @click="refreshData">
        <RefreshCcw class="h-4 w-4" />
        刷新数据
      </Button>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card class="bg-card text-card-foreground">
        <CardContent class="p-5">
          <div class="flex items-center gap-4">
            <div class="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <Users class="h-6 w-6" />
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">{{ stats.totalAccounts }}</div>
              <div class="mt-1 text-xs text-muted-foreground">总账号数</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="bg-card text-card-foreground">
        <CardContent class="p-5">
          <div class="flex items-center gap-4">
            <div class="h-12 w-12 rounded-xl bg-emerald-500/10 text-emerald-700 flex items-center justify-center">
              <BadgeCheck class="h-6 w-6" />
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">{{ stats.subscribedAccounts }}</div>
              <div class="mt-1 text-xs text-muted-foreground">已订阅</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="bg-card text-card-foreground">
        <CardContent class="p-5">
          <div class="flex items-center gap-4">
            <div class="h-12 w-12 rounded-xl bg-amber-500/10 text-amber-700 flex items-center justify-center">
              <CreditCard class="h-6 w-6" />
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">{{ stats.availableCards }}</div>
              <div class="mt-1 text-xs text-muted-foreground">可用卡片</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="bg-card text-card-foreground">
        <CardContent class="p-5">
          <div class="flex items-center gap-4">
            <div class="h-12 w-12 rounded-xl bg-rose-500/10 text-rose-700 flex items-center justify-center">
              <Timer class="h-6 w-6" />
            </div>
            <div class="min-w-0">
              <div class="text-2xl font-semibold leading-none">{{ stats.runningTasks }}</div>
              <div class="mt-1 text-xs text-muted-foreground">运行中任务</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader class="pb-2">
        <CardTitle class="text-base">最近任务</CardTitle>
        <CardDescription>最近 3 条记录（示例数据）</CardDescription>
      </CardHeader>
      <CardContent class="pt-2">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务ID</TableHead>
                <TableHead>任务类型</TableHead>
                <TableHead>关联账号</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>进度</TableHead>
                <TableHead>创建时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="row in recentTasks" :key="row.id">
                <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>
                <TableCell>{{ row.type }}</TableCell>
                <TableCell>{{ row.account }}</TableCell>
                <TableCell>
                  <Badge :variant="getStatusVariant(row.status)" class="rounded-full">
                    {{ row.status }}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div class="flex items-center gap-3">
                    <div class="h-2 w-28 rounded-full bg-muted overflow-hidden">
                      <div class="h-full rounded-full bg-primary" :class="progressWidthClass(row.progress)" />
                    </div>
                    <span class="text-xs text-muted-foreground tabular-nums">{{ row.progress }}%</span>
                  </div>
                </TableCell>
                <TableCell class="text-muted-foreground">{{ formatDate(row.created_at) }}</TableCell>
              </TableRow>

              <TableRow v-if="!loading && recentTasks.length === 0">
                <TableCell class="py-8 text-center text-muted-foreground" colspan="6">暂无任务</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { BadgeCheck, CreditCard, RefreshCcw, Timer, Users } from 'lucide-vue-next'
import { googleAccountsApi } from '@/api/google'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const loading = ref(false)

const stats = reactive({
  totalAccounts: 0,
  subscribedAccounts: 0,
  availableCards: 0,
  runningTasks: 0
})

const recentTasks = ref([
  { id: 1, type: '一键全自动', account: 'test@gmail.com', status: '运行中', progress: 60, created_at: new Date().toISOString() },
  { id: 2, type: 'SheerID验证', account: 'demo@gmail.com', status: '已完成', progress: 100, created_at: new Date().toISOString() },
  { id: 3, type: '自动绑卡', account: 'user@gmail.com', status: '失败', progress: 30, created_at: new Date().toISOString() }
])

const fetchStats = async () => {
  loading.value = true
  try {
    const accountsResponse = await googleAccountsApi.getAccounts({ page_size: 1000 })
    // 兼容后端返回数组或分页对象两种情况
    if (Array.isArray(accountsResponse)) {
      stats.totalAccounts = accountsResponse.length
      stats.subscribedAccounts = accountsResponse.filter((a: any) => a.gemini_status === 'active').length
    } else if (accountsResponse.count !== undefined) {
      stats.totalAccounts = accountsResponse.count
      // 需要单独请求已订阅数量
      const subscribedResponse = await googleAccountsApi.getAccounts({ 
        status: 'subscribed',
        page_size: 1 
      })
      stats.subscribedAccounts = subscribedResponse.count || 0
    } else {
      stats.totalAccounts = 0
      stats.subscribedAccounts = 0
    }
    
    // TODO: 获取其他统计数据
    stats.availableCards = 0
    stats.runningTasks = 0
  } catch (error) {
    console.error('获取统计数据失败:', error)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchStats()
  ElMessage.success('数据已刷新')
}

const getStatusVariant = (status: string) => {
  const map: Record<string, any> = {
    '运行中': 'secondary',
    '已完成': 'default',
    '失败': 'destructive',
    '等待中': 'outline'
  }
  return map[status] || 'secondary'
}

const progressWidthClass = (progress: number) => {
  const p = Math.max(0, Math.min(100, Number(progress) || 0))
  if (p <= 0) return 'w-0'
  if (p <= 10) return 'w-1/6'
  if (p <= 20) return 'w-1/5'
  if (p <= 30) return 'w-1/4'
  if (p <= 40) return 'w-1/3'
  if (p <= 50) return 'w-1/2'
  if (p <= 60) return 'w-3/5'
  if (p <= 70) return 'w-2/3'
  if (p <= 80) return 'w-3/4'
  if (p <= 90) return 'w-5/6'
  return 'w-full'
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchStats()
})
</script>
