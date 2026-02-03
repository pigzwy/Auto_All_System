<template>
  <div class="relative min-h-screen overflow-hidden bg-gradient-to-br from-muted/40 via-background to-muted/60">
    <div
      aria-hidden="true"
      class="pointer-events-none absolute inset-0 bg-gradient-to-br from-sky-500/15 via-emerald-500/10 to-amber-500/15"
    />
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -top-28 -right-24 h-80 w-80 rounded-full bg-sky-400/20 blur-3xl"
    />
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -bottom-28 -left-24 h-80 w-80 rounded-full bg-amber-400/25 blur-3xl"
    />

    <div class="relative flex min-h-screen items-center justify-center p-6">
      <Card class="w-full max-w-md overflow-hidden rounded-2xl border border-border/80 bg-card text-card-foreground shadow-2xl">
        <CardHeader>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 font-semibold text-primary">
              AA
            </div>
            <div class="min-w-0">
              <h2 class="text-lg font-semibold leading-none">Auto All System</h2>
              <p class="mt-1 text-sm text-muted-foreground">自动化平台登录</p>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <form class="space-y-5" @submit.prevent="handleSubmit">
            <div class="grid gap-2">
              <label class="text-sm font-medium text-foreground">用户名</label>
              <div class="relative">
                <User class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  v-model="form.username"
                  placeholder="请输入用户名"
                  autocomplete="username"
                  class="h-11 pl-9"
                  autofocus
                />
              </div>
              <p v-if="errors.username" class="text-xs text-rose-600">{{ errors.username }}</p>
            </div>

            <div class="grid gap-2">
              <label class="text-sm font-medium text-foreground">密码</label>
              <div class="relative">
                <Lock class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="请输入密码"
                  autocomplete="current-password"
                  class="h-11 pl-9 pr-14"
                />
                <button
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  @click="showPassword = !showPassword"
                >
                  {{ showPassword ? '隐藏' : '显示' }}
                </button>
              </div>
              <p v-if="errors.password" class="text-xs text-rose-600">{{ errors.password }}</p>
            </div>

            <Button type="submit" class="h-11 w-full gap-2" :disabled="loading">
              <Loading v-if="loading" class="h-4 w-4 animate-spin" />
              登录
            </Button>

            <p class="-mt-1 text-center text-xs text-muted-foreground">
              密码至少 6 位
            </p>

            <div class="pt-2 text-center">
              <router-link
                to="/register"
                class="text-sm text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
              >
                还没有账号？立即注册
              </router-link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Loading } from '@/icons'
import { ElMessage } from '@/lib/element'
import { useUserStore } from '@/stores/user'
import type { LoginForm } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

const router = useRouter()
const userStore = useUserStore()

  const loading = ref(false)
  const showPassword = ref(false)

const form = reactive<LoginForm>({
  username: '',
  password: ''
})

const errors = reactive({
  username: '',
  password: '',
})

const validate = () => {
  errors.username = form.username.trim() ? '' : '请输入用户名'
  if (!form.password) {
    errors.password = '请输入密码'
  } else if (form.password.length < 6) {
    errors.password = '密码至少6位'
  } else {
    errors.password = ''
  }
  return !errors.username && !errors.password
}

const handleSubmit = async () => {
  if (!validate()) return
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push({ name: 'Dashboard' })
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
