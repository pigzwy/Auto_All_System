<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-semibold text-foreground">一键全自动</h2>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>全流程自动化</CardTitle>
        <CardDescription>按顺序执行：登录 -> 检测 -> 验证 -> 订阅</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="space-y-6 max-w-lg">
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

          <div class="space-y-3">
            <label class="text-sm font-medium">包含步骤</label>
            <div class="space-y-2">
              <div class="flex items-center space-x-2">
                <Switch :checked="form.steps.login" @update:checked="form.steps.login = $event" />
                <span class="text-sm">登录检测</span>
              </div>
              <div class="flex items-center space-x-2">
                <Switch :checked="form.steps.verify" @update:checked="form.steps.verify = $event" />
                <span class="text-sm">SheerID 验证</span>
              </div>
              <div class="flex items-center space-x-2">
                <Switch :checked="form.steps.bind" @update:checked="form.steps.bind = $event" />
                <span class="text-sm">自动绑卡</span>
              </div>
              <div class="flex items-center space-x-2">
                <Switch :checked="form.steps.subscribe" @update:checked="form.steps.subscribe = $event" />
                <span class="text-sm">执行订阅</span>
              </div>
            </div>
          </div>

          <Button :disabled="running" @click="startTask" class="w-full">
            <Play class="mr-2 h-4 w-4" /> 开始全流程
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
import { Switch } from '@/components/ui/switch'

const running = ref(false)
const groups = ref<any[]>([])
const form = reactive({
  group: '',
  steps: {
    login: true,
    verify: true,
    bind: true,
    subscribe: true
  }
})

const startTask = () => {
  // start logic
}
</script>
