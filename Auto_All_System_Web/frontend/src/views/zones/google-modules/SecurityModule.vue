<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-semibold text-foreground">安全设置</h2>
    </div>

    <div class="grid gap-6 md:grid-cols-2">
      <Card class="bg-card text-card-foreground">
        <CardHeader>
          <CardTitle>2FA设置</CardTitle>
          <CardDescription>批量修改或添加2FA验证</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="space-y-4">
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
            <Button class="w-full" :disabled="loading" @click="handleUpdate2FA">
              <Shield class="mr-2 h-4 w-4" /> 更新 2FA
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card class="bg-card text-card-foreground">
        <CardHeader>
          <CardTitle>辅助邮箱</CardTitle>
          <CardDescription>批量修改辅助验证邮箱</CardDescription>
        </CardHeader>
        <CardContent>
          <div class="space-y-4">
            <div class="grid gap-2">
              <label class="text-sm font-medium">新辅助邮箱</label>
              <Input v-model="form.recoveryEmail" placeholder="留空则随机生成" />
            </div>
            <Button class="w-full" variant="secondary" :disabled="loading" @click="handleUpdateRecovery">
              <Mail class="mr-2 h-4 w-4" /> 更新辅助邮箱
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Shield, Mail } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const loading = ref(false)
const groups = ref<any[]>([])
const form = reactive({
  group: '',
  recoveryEmail: ''
})

const handleUpdate2FA = () => {
  // update logic
}

const handleUpdateRecovery = () => {
  // update logic
}
</script>
