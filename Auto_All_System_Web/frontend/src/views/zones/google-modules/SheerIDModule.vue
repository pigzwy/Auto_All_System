<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-semibold text-foreground">SheerID 验证</h2>
      <Button variant="outline" size="sm" class="gap-2" @click="handleRefresh">
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
        刷新
      </Button>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>批量验证</CardTitle>
        <CardDescription>选择账号进行SheerID学生认证</CardDescription>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="flex items-center gap-4">
          <Select v-model="selectedGroup">
            <SelectTrigger class="w-[200px]">
              <SelectValue placeholder="选择分组" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分组</SelectItem>
              <SelectItem v-for="group in groups" :key="group.id" :value="String(group.id)">
                {{ group.name }}
              </SelectItem>
            </SelectContent>
          </Select>
          
          <Button :disabled="processing" @click="startVerification">
            <Play class="mr-2 h-4 w-4" /> 开始验证
          </Button>
        </div>

        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>邮箱</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>进度</TableHead>
                <TableHead class="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="task in tasks" :key="task.id">
                <TableCell>{{ task.email }}</TableCell>
                <TableCell>
                  <Badge :variant="getStatusVariant(task.status)">{{ task.status }}</Badge>
                </TableCell>
                <TableCell>
                  <div class="w-full max-w-xs">
                    <div class="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div class="h-full bg-primary transition-all" :style="{ width: `${task.progress}%` }" />
                    </div>
                  </div>
                </TableCell>
                <TableCell class="text-right">
                  <Button variant="ghost" size="xs" @click="viewLogs(task)">日志</Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="tasks.length === 0">
                <TableCell colspan="4" class="py-8 text-center text-muted-foreground">暂无任务</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Play, RefreshCw } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'

const loading = ref(false)
const processing = ref(false)
const selectedGroup = ref('all')
const groups = ref<any[]>([])
const tasks = ref<any[]>([])

const handleRefresh = () => {
  // refresh logic
}

const startVerification = () => {
  // start logic
}

const viewLogs = (_task: any) => {
  // view logs
}

const getStatusVariant = (status: string) => {
  switch (status) {
    case 'success': return 'default'
    case 'failed': return 'destructive'
    case 'processing': return 'secondary'
    default: return 'outline'
  }
}
</script>
