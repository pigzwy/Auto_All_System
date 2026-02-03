<template>
  <div class="space-y-6 p-5">
    <div>
      <h1 class="text-2xl font-semibold text-foreground">任务管理</h1>
    </div>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="space-y-6 p-6">
      <!-- 统计卡片 -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="flex items-center gap-4 rounded-xl border border-border bg-background/70 p-5 shadow-sm">
          <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-sky-500/10 text-2xl">📋</div>
          <div>
            <div class="text-2xl font-bold leading-none text-foreground">{{ taskStats.pending }}</div>
            <div class="mt-1 text-sm text-muted-foreground">待处理</div>
          </div>
        </div>
        <div class="flex items-center gap-4 rounded-xl border border-border bg-background/70 p-5 shadow-sm">
          <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-amber-500/10 text-2xl">🏃</div>
          <div>
            <div class="text-2xl font-bold leading-none text-foreground">{{ taskStats.running }}</div>
            <div class="mt-1 text-sm text-muted-foreground">执行中</div>
          </div>
        </div>
        <div class="flex items-center gap-4 rounded-xl border border-border bg-background/70 p-5 shadow-sm">
          <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-500/10 text-2xl">✅</div>
          <div>
            <div class="text-2xl font-bold leading-none text-foreground">{{ taskStats.success }}</div>
            <div class="mt-1 text-sm text-muted-foreground">已完成</div>
          </div>
        </div>
        <div class="flex items-center gap-4 rounded-xl border border-border bg-background/70 p-5 shadow-sm">
          <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-rose-500/10 text-2xl">❌</div>
          <div>
            <div class="text-2xl font-bold leading-none text-foreground">{{ taskStats.failed }}</div>
            <div class="mt-1 text-sm text-muted-foreground">失败</div>
          </div>
        </div>
      </div>

      <!-- 任务列表 -->
      <DataTable :data="tasks" v-loading="loading" stripe class="mt-5 w-full">
        <DataColumn prop="id" label="ID" width="80" />
        <DataColumn prop="user" label="用户" width="120">
          <template #default="{ row }">
            {{ row.user?.username || row.user }}
          </template>
        </DataColumn>
        <DataColumn prop="zone" label="专区" width="120" />
        <DataColumn prop="task_type" label="任务类型" width="150" />
        <DataColumn prop="status" label="状态" width="100">
          <template #default="{ row }">
            <Tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</Tag>
          </template>
        </DataColumn>
        <DataColumn prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <ProgressBar :percentage="row.progress" />
          </template>
        </DataColumn>
        <DataColumn prop="cost_amount" label="费用" width="100" />
        <DataColumn prop="created_at" label="创建时间" />
        <DataColumn label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <Button text  variant="default" type="button" @click="viewDetail(row)">详情</Button>
            <Button text  variant="destructive" type="button" @click="deleteTask(row)">删除</Button>
          </template>
        </DataColumn>
      </DataTable>

      <Paginator
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next"
        class="mt-5 justify-center"
        @current-change="fetchTasks"
        @size-change="fetchTasks"
      />
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { tasksApi } from '@/api/tasks'
import { ElMessage, ElMessageBox } from '@/lib/element'
import type { Task } from '@/types'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const tasks = ref<Task[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const taskStats = reactive({
  pending: 0,
  running: 0,
  success: 0,
  failed: 0
})

const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await tasksApi.getTasks({
      page: currentPage.value,
      page_size: pageSize.value
    })
    tasks.value = response.results
    total.value = response.count
    
    // 更新统计
    taskStats.pending = response.results.filter((t: any) => t.status === 'pending').length
    taskStats.running = response.results.filter((t: any) => t.status === 'running').length
    taskStats.success = response.results.filter((t: any) => t.status === 'success').length
    taskStats.failed = response.results.filter((t: any) => t.status === 'failed').length
  } catch (error) {
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const getStatusType = (status: string) => {
  const map: Record<string, any> = {
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待处理',
    running: '执行中',
    success: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const viewDetail = async (task: Task) => {
  try {
    const logs = await tasksApi.getTaskLogs(task.id)
    let logsHtml = logs.length > 0
      ? logs.map((log: any) => `<p style="margin: 5px 0;">${log.message}</p>`).join('')
      : '<p>暂无日志</p>'
    
    await ElMessage.info({
      dangerouslyUseHTMLString: true,
      message: `
        <div style="text-align: left;">
          <p><strong>任务ID：</strong>${task.id}</p>
          <p><strong>任务类型：</strong>${task.task_type}</p>
          <p><strong>状态：</strong>${getStatusText(task.status)}</p>
          <p><strong>进度：</strong>${task.progress}%</p>
          <p><strong>费用：</strong>¥${task.cost_amount || 0}</p>
          <p><strong>日志：</strong></p>
          ${logsHtml}
        </div>
      `,
      duration: 5000
    })
  } catch (error) {
    console.error('Failed to fetch task details:', error)
    ElMessage.error('获取任务详情失败')
  }
}

const deleteTask = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务 #${task.id} 吗？此操作不可恢复！`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await tasksApi.deleteTask(task.id)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to delete task:', error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchTasks()
})
</script>
