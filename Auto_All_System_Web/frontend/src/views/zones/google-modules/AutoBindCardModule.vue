<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-semibold text-foreground">自动绑卡</h2>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>任务配置</CardTitle>
        <CardDescription>配置自动绑卡任务参数</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="space-y-4 max-w-lg">
          <div class="grid gap-2">
            <label class="text-sm font-medium">选择分组</label>
            <Select v-model="form.group">
              <SelectTrigger>
                <SelectValue placeholder="请选择" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">并发数量</label>
            <Input v-model="form.threads" type="number" :min="1" :max="50" />
          </div>

          <div class="flex items-center space-x-2">
            <Switch :checked="form.retry" @update:checked="form.retry = $event" />
            <label class="text-sm font-medium">失败自动重试</label>
          </div>

          <Button :disabled="running" @click="startTask">
            <Play class="mr-2 h-4 w-4" /> 开始任务
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>执行日志</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="h-64 rounded-md border border-input bg-muted/50 p-4 font-mono text-xs overflow-y-auto">
          <div v-for="(log, i) in logs" :key="i" class="mb-1">
            <span class="text-muted-foreground">[{{ log.time }}]</span> {{ log.message }}
          </div>
          <div v-if="logs.length === 0" class="text-muted-foreground text-center mt-20">暂无日志</div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Play } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'

const running = ref(false)
const groups = ref<any[]>([])
const logs = ref<any[]>([])
const form = reactive({
  group: '',
  threads: 5,
  retry: false
})

const startTask = () => {
  // start logic
}
</script>
