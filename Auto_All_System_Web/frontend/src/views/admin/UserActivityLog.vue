<template>
  <div class="space-y-6 p-5">
    <div>
      <h1 class="text-2xl font-semibold text-foreground">用户操作日志</h1>
      <p class="mt-1 text-sm text-muted-foreground">用于审计关键操作、排查异常行为。</p>
    </div>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="space-y-4 p-6">
        <div class="flex flex-wrap items-end gap-4">
          <div class="grid gap-2">
            <label class="text-sm text-muted-foreground">用户</label>
            <Input v-model="filters.username" placeholder="用户名" class="h-9 w-full sm:w-56" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm text-muted-foreground">操作类型</label>
            <Select v-model="filters.action">
              <SelectTrigger class="w-full sm:w-48">
                <SelectValue placeholder="选择类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">全部</SelectItem>
                <SelectItem value="login">登录</SelectItem>
                <SelectItem value="logout">登出</SelectItem>
                <SelectItem value="create_task">创建任务</SelectItem>
                <SelectItem value="recharge">充值</SelectItem>
                <SelectItem value="subscribe">订阅VIP</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid gap-2">
            <label class="text-sm text-muted-foreground">日期</label>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
              <Input v-model="dateStart" type="date" class="h-9 w-full sm:w-40" />
              <span class="text-xs text-muted-foreground">至</span>
              <Input v-model="dateEnd" type="date" class="h-9 w-full sm:w-40" />
            </div>
          </div>

          <div class="flex items-center gap-2">
            <Button variant="default" type="button" @click="fetchLogs">查询</Button>
            <Button variant="secondary" type="button" @click="resetFilters">重置</Button>
          </div>
        </div>

        <div class="overflow-hidden rounded-xl border border-border" v-loading="loading">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[80px]">ID</TableHead>
                <TableHead class="w-[120px]">用户</TableHead>
                <TableHead class="w-[120px]">操作</TableHead>
                <TableHead>描述</TableHead>
                <TableHead class="w-[140px]">IP地址</TableHead>
                <TableHead class="w-[220px]">User Agent</TableHead>
                <TableHead class="w-[180px]">时间</TableHead>
                <TableHead class="w-[100px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, idx) in logs" :key="row.id ?? idx" :class="idx % 2 === 1 ? 'bg-muted/10' : ''">
                <TableCell class="w-[80px]">{{ row.id }}</TableCell>
                <TableCell class="w-[120px]">{{ row.username }}</TableCell>
                <TableCell class="w-[120px]">
                  <Badge variant="outline" class="rounded-full" :class="getActionBadgeClass(row.action)">
                    {{ getActionName(row.action) }}
                  </Badge>
                </TableCell>
                <TableCell class="text-foreground">{{ row.description }}</TableCell>
                <TableCell class="w-[140px]">{{ row.ip_address }}</TableCell>
                <TableCell class="w-[220px]">
                  <span class="block truncate" :title="row.user_agent">{{ row.user_agent }}</span>
                </TableCell>
                <TableCell class="w-[180px]">{{ row.created_at }}</TableCell>
                <TableCell class="w-[100px] text-right">
                  <Button type="button" variant="ghost" size="sm" @click="viewDetail(row)">详情</Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="!logs.length">
                <TableCell :colspan="8" class="py-10 text-center text-sm text-muted-foreground">暂无数据</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="text-sm text-muted-foreground">共 {{ total }} 条</div>
          <div class="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" :disabled="currentPage <= 1" @click="goPrev">上一页</Button>
            <span class="text-sm text-muted-foreground">{{ currentPage }} / {{ totalPages }}</span>
            <Button type="button" variant="outline" size="sm" :disabled="currentPage >= totalPages" @click="goNext">下一页</Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 详情对话框 -->
    <Dialog v-model:open="dialogVisible">
      <DialogContent class="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>日志详情</DialogTitle>
        </DialogHeader>

        <div v-if="currentLog" class="grid gap-3 py-2 text-sm">
          <div class="grid grid-cols-[120px_1fr] gap-3">
            <span class="text-muted-foreground">ID</span>
            <span class="text-foreground">{{ currentLog.id }}</span>
          </div>
          <div class="grid grid-cols-[120px_1fr] gap-3">
            <span class="text-muted-foreground">用户</span>
            <span class="text-foreground">{{ currentLog.username }}</span>
          </div>
          <div class="grid grid-cols-[120px_1fr] gap-3">
            <span class="text-muted-foreground">操作</span>
            <span class="text-foreground">{{ getActionName(currentLog.action) }}</span>
          </div>
          <div class="grid grid-cols-[120px_1fr] gap-3">
            <span class="text-muted-foreground">描述</span>
            <span class="text-foreground">{{ currentLog.description }}</span>
          </div>
          <div class="grid grid-cols-[120px_1fr] gap-3">
            <span class="text-muted-foreground">IP地址</span>
            <span class="text-foreground">{{ currentLog.ip_address }}</span>
          </div>
          <div class="grid grid-cols-[120px_1fr] gap-3">
            <span class="text-muted-foreground">User Agent</span>
            <span class="break-words text-foreground">{{ currentLog.user_agent }}</span>
          </div>
          <div class="grid grid-cols-[120px_1fr] gap-3">
            <span class="text-muted-foreground">时间</span>
            <span class="text-foreground">{{ currentLog.created_at }}</span>
          </div>

          <div v-if="currentLog.extra_data" class="grid gap-2">
            <span class="text-muted-foreground">额外数据</span>
            <pre class="max-h-[220px] overflow-x-auto rounded-md bg-muted/30 p-3 text-xs text-foreground">{{ JSON.stringify(currentLog.extra_data, null, 2) }}</pre>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="secondary" @click="dialogVisible = false">关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { Card, CardContent } from '@/components/ui/card'

type ActivityLogRow = {
  id: number
  username: string
  action: string
  description: string
  ip_address: string
  user_agent: string
  created_at: string
  extra_data?: unknown
}

const loading = ref(false)
const logs = ref<ActivityLogRow[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const currentLog = ref<ActivityLogRow | null>(null)

const filters = reactive({
  username: '',
  action: '',
  dateRange: ['', ''] as [string, string]
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const dateStart = computed({
  get: () => filters.dateRange[0] || '',
  set: (val: string) => {
    filters.dateRange = [val, filters.dateRange[1] || '']
  },
})

const dateEnd = computed({
  get: () => filters.dateRange[1] || '',
  set: (val: string) => {
    filters.dateRange = [filters.dateRange[0] || '', val]
  },
})

const fetchLogs = async () => {
  loading.value = true
  try {
    // TODO: 调用日志API
    logs.value = []
    total.value = 0
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.username = ''
  filters.action = ''
  filters.dateRange = ['', '']
  fetchLogs()
}

const getActionBadgeClass = (action: string) => {
  const map: Record<string, string> = {
    login: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700',
    logout: 'border-slate-500/20 bg-slate-500/10 text-slate-700',
    create_task: 'border-primary/20 bg-primary/10 text-primary',
    recharge: 'border-amber-500/20 bg-amber-500/10 text-amber-800',
    subscribe: 'border-rose-500/20 bg-rose-500/10 text-rose-700'
  }
  return map[action] || 'border-border bg-muted/10 text-foreground'
}

const getActionName = (action: string) => {
  const map: Record<string, string> = {
    login: '登录',
    logout: '登出',
    create_task: '创建任务',
    recharge: '充值',
    subscribe: '订阅VIP'
  }
  return map[action] || action
}

const viewDetail = (row: ActivityLogRow) => {
  currentLog.value = row
  dialogVisible.value = true
}

const goPrev = () => {
  if (currentPage.value <= 1) return
  currentPage.value -= 1
  fetchLogs()
}

const goNext = () => {
  if (currentPage.value >= totalPages.value) return
  currentPage.value += 1
  fetchLogs()
}

onMounted(() => {
  fetchLogs()
})
</script>
