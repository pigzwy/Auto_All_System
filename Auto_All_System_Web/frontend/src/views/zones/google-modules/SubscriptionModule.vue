<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-semibold text-foreground">订阅管理</h2>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>批量订阅</CardTitle>
        <CardDescription>自动化执行订阅操作</CardDescription>
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
            <label class="text-sm font-medium">操作类型</label>
            <Select v-model="form.action">
              <SelectTrigger>
                <SelectValue placeholder="请选择" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="check">检查状态</SelectItem>
                <SelectItem value="subscribe">执行订阅</SelectItem>
                <SelectItem value="cancel">取消订阅</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button :disabled="running" @click="startTask">
            <Play class="mr-2 h-4 w-4" /> 执行操作
          </Button>
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const running = ref(false)
const groups = ref<any[]>([])
const form = reactive({
  group: '',
  action: 'check'
})

const startTask = () => {
  // start logic
}
</script>
