<template>
  <div class="space-y-6 p-5">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <Button variant="ghost" size="sm" class="gap-2" @click="router.back()">
          <ArrowLeft class="h-4 w-4" />
          返回
        </Button>
        <h1 class="text-2xl font-semibold text-foreground">Google 业务任务管理</h1>
      </div>
      <Button variant="success" size="sm" class="gap-2" @click="router.push('/admin/google-business/tasks/create')">
        <Plus class="h-4 w-4" />
        创建任务
      </Button>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">任务类型</span>
            <Select v-model="searchForm.task_type" @update:modelValue="handleSearch">
              <SelectTrigger class="w-[160px]">
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="one_click">一键全自动</SelectItem>
                <SelectItem value="register">注册账号</SelectItem>
                <SelectItem value="login">登录检测</SelectItem>
                <SelectItem value="verify">验证/绑卡</SelectItem>
                <SelectItem value="subscribe">订阅操作</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">状态</span>
            <Select v-model="searchForm.status" @update:modelValue="handleSearch">
              <SelectTrigger class="w-[140px]">
                <SelectValue placeholder="全部状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="pending">等待中</SelectItem>
                <SelectItem value="processing">进行中</SelectItem>
                <SelectItem value="completed">已完成</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
                <SelectItem value="cancelled">已取消</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">搜索</span>
            <Input
              v-model="searchForm.email"
              placeholder="搜索账号邮箱"
              class="w-[200px]"
              @keydown.enter="handleSearch"
            />
          </div>

          <div class="flex items-center gap-2 ml-auto">
            <Button variant="outline" size="sm" @click="handleReset">重置</Button>
            <Button size="sm" class="gap-2" @click="handleSearch">
              <Search class="h-4 w-4" />
              搜索
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent class="p-0">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-20">ID</TableHead>
                <TableHead class="min-w-[140px]">任务类型</TableHead>
                <TableHead class="min-w-[220px]">关联账号</TableHead>
                <TableHead class="w-32">状态</TableHead>
                <TableHead class="min-w-[160px]">进度</TableHead>
                <TableHead class="min-w-[200px]">结果/错误</TableHead>
                <TableHead class="w-40">创建时间</TableHead>
                <TableHead class="w-24 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="loading && tasks.length === 0">
                <TableCell colspan="8" class="py-10 text-center">
                  <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                </TableCell>
              </TableRow>
              <TableRow v-else v-for="row in tasks" :key="row.id" class="hover:bg-muted/20">
                <TableCell class="font-mono text-xs text-muted-foreground">#{{ row.id }}</TableCell>
                <TableCell>
                  <div class="flex items-center gap-2">
                    <span class="font-medium">{{ getTaskTypeName(row.task_type) }}</span>
                    <Badge v-if="row.task_type === 'one_click'" variant="secondary" class="text-[10px] h-5 px-1">全自动</Badge>
                  </div>
                </TableCell>
                <TableCell class="font-mono text-xs">{{ row.account_email }}</TableCell>
                <TableCell>
                  <Badge :variant="getStatusVariant(row.status)" class="rounded-full">
                    {{ getStatusText(row.status) }}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div class="flex items-center gap-3">
                    <div class="h-2 w-24 rounded-full bg-muted overflow-hidden">
                      <div class="h-full rounded-full bg-primary" :class="progressWidthClass(row.progress_percentage)" />
                    </div>
                    <span class="text-xs text-muted-foreground tabular-nums">{{ row.progress_percentage || 0 }}%</span>
                  </div>
                  <div v-if="row.current_step" class="text-[10px] text-muted-foreground mt-1 truncate max-w-[140px]" :title="row.current_step">
                    {{ row.current_step }}
                  </div>
                </TableCell>
                <TableCell>
                  <span v-if="row.error_message" class="text-xs text-destructive line-clamp-2" :title="row.error_message">
                    {{ row.error_message }}
                  </span>
                  <span v-else-if="row.result_data" class="text-xs text-muted-foreground line-clamp-2">
                    {{ JSON.stringify(row.result_data) }}
                  </span>
                  <span v-else class="text-xs text-muted-foreground">-</span>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground">{{ formatDate(row.created_at) }}</TableCell>
                <TableCell class="text-right">
                  <Button variant="outline" size="xs" @click="viewDetail(row)">详情</Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="!loading && tasks.length === 0">
                <TableCell colspan="8" class="py-10 text-center text-sm text-muted-foreground">暂无任务数据</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div class="p-4 flex items-center justify-end gap-2" v-if="total > pageSize">
          <Button variant="outline" size="sm" :disabled="currentPage <= 1" @click="currentPage--; fetchTasks()">上一页</Button>
          <div class="text-sm text-muted-foreground">
            第 <span class="font-medium text-foreground">{{ currentPage }}</span> 页
          </div>
          <Button variant="outline" size="sm" :disabled="tasks.length < pageSize" @click="currentPage++; fetchTasks()">下一页</Button>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '@/lib/element'
import { ArrowLeft, Plus, Search, Loader2 } from 'lucide-vue-next'
import googleBusinessApi from '@/api/google_business'
import dayjs from 'dayjs'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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
const tasks = ref<any[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const searchForm = reactive({
  task_type: 'all',
  status: 'all',
  email: ''
})

const fetchTasks = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
      ordering: '-created_at'
    }
    
    if (searchForm.task_type !== 'all') params.task_type = searchForm.task_type
    if (searchForm.status !== 'all') params.status = searchForm.status
    if (searchForm.email) params.account_email__icontains = searchForm.email

    const res: any = await googleBusinessApi.getTasks(params)
    if (res && res.results) {
      tasks.value = res.results
      total.value = res.count
    }
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchTasks()
}

const handleReset = () => {
  searchForm.task_type = 'all'
  searchForm.status = 'all'
  searchForm.email = ''
  handleSearch()
}

const viewDetail = (row: any) => {
  router.push(`/admin/google-business/tasks/${row.id}`)
}

const getTaskTypeName = (type: string) => {
  const map: Record<string, string> = {
    one_click: '一键全自动',
    register: '注册账号',
    login: '登录检测',
    verify: '验证/绑卡',
    subscribe: '订阅操作'
  }
  return map[type] || type
}

const getStatusVariant = (status: string) => {
  const map: Record<string, any> = {
    pending: 'outline',
    processing: 'secondary', // Use secondary or warning-like if customized
    completed: 'default', // Usually green/primary
    failed: 'destructive',
    cancelled: 'outline'
  }
  return map[status] || 'outline'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    processing: '进行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return map[status] || status
}

const progressWidthClass = (progress: number) => {
  const p = Math.max(0, Math.min(100, Number(progress) || 0))
  if (p <= 0) return 'w-0'
  // Simplified percentages for Tailwind classes
  if (p <= 10) return 'w-[10%]'
  if (p <= 20) return 'w-[20%]'
  if (p <= 30) return 'w-[30%]'
  if (p <= 40) return 'w-[40%]'
  if (p <= 50) return 'w-[50%]'
  if (p <= 60) return 'w-[60%]'
  if (p <= 70) return 'w-[70%]'
  if (p <= 80) return 'w-[80%]'
  if (p <= 90) return 'w-[90%]'
  return 'w-full'
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchTasks()
})
</script>
