<template>
  <div class="relative min-h-screen overflow-hidden bg-muted/30">
    <div
      aria-hidden="true"
      class="pointer-events-none absolute inset-0 bg-gradient-to-br from-indigo-500/15 via-sky-500/10 to-fuchsia-500/15"
    />
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -top-28 -right-24 h-80 w-80 rounded-full bg-primary/15 blur-3xl"
    />
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -bottom-28 -left-24 h-80 w-80 rounded-full bg-secondary/40 blur-3xl"
    />

    <div class="relative flex min-h-screen items-center justify-center p-6">
      <Card class="w-full max-w-md overflow-hidden rounded-2xl border border-border bg-card text-card-foreground shadow-xl">
        <CardHeader>
          <div class="flex items-start gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 font-semibold text-primary">
              AA
            </div>
            <div class="min-w-0">
              <h2 class="text-lg font-semibold leading-none">Auto All System</h2>
              <p class="mt-1 text-sm text-muted-foreground">注册新账号</p>
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
              <label class="text-sm font-medium text-foreground">邮箱</label>
              <div class="relative">
                <Mail class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  v-model="form.email"
                  type="email"
                  placeholder="请输入邮箱"
                  autocomplete="email"
                  class="h-11 pl-9"
                />
              </div>
              <p v-if="errors.email" class="text-xs text-rose-600">{{ errors.email }}</p>
            </div>

            <div class="grid gap-2">
              <label class="text-sm font-medium text-foreground">密码</label>
              <div class="relative">
                <Lock class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="请输入密码"
                  autocomplete="new-password"
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

            <div class="grid gap-2">
              <label class="text-sm font-medium text-foreground">确认密码</label>
              <div class="relative">
                <Lock class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  v-model="form.password_confirm"
                  :type="showConfirmPassword ? 'text' : 'password'"
                  placeholder="请再次输入密码"
                  autocomplete="new-password"
                  class="h-11 pl-9 pr-14"
                />
                <button
                  type="button"
                  class="absolute right-2 top-1/2 -translate-y-1/2 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                  @click="showConfirmPassword = !showConfirmPassword"
                >
                  {{ showConfirmPassword ? '隐藏' : '显示' }}
                </button>
              </div>
              <p v-if="errors.password_confirm" class="text-xs text-rose-600">{{ errors.password_confirm }}</p>
            </div>

            <Button type="submit" class="w-full gap-2" :disabled="loading">
              <Loading v-if="loading" class="h-4 w-4 animate-spin" />
              注册
            </Button>

            <p class="-mt-1 text-center text-xs text-muted-foreground">
              密码至少 6 位；注册后可在个人中心完善信息
            </p>

            <div class="pt-2 text-center">
              <router-link
                to="/login"
                class="text-sm text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
              >
                已有账号？立即登录
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
import { User, Mail, Lock, Loading } from '@/icons'
import { ElMessage } from '@/lib/element'
import { useUserStore } from '@/stores/user'
import type { RegisterForm } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)

const form = reactive<RegisterForm>({
  username: '',
  email: '',
  password: '',
  password_confirm: ''
})

const errors = reactive({
  username: '',
  email: '',
  password: '',
  password_confirm: '',
})

const validateEmail = (value: string) => {
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRe.test(value)
}

const validate = () => {
  const u = form.username.trim()
  errors.username = !u ? '请输入用户名' : u.length < 3 || u.length > 30 ? '用户名长度3-30位' : ''

  const e = form.email.trim()
  if (!e) errors.email = '请输入邮箱'
  else if (!validateEmail(e)) errors.email = '请输入正确的邮箱'
  else errors.email = ''

  if (!form.password) errors.password = '请输入密码'
  else if (form.password.length < 6) errors.password = '密码至少6位'
  else errors.password = ''

  if (!form.password_confirm) errors.password_confirm = '请再次输入密码'
  else if (form.password_confirm !== form.password) errors.password_confirm = '两次输入的密码不一致'
  else errors.password_confirm = ''

  return !errors.username && !errors.email && !errors.password && !errors.password_confirm
}

const handleSubmit = async () => {
  if (!validate()) return

  loading.value = true
  try {
    await userStore.register(form)
    ElMessage.success('注册成功')
    router.push({ name: 'Dashboard' })
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>
