<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold text-foreground">个人资料</h1>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>基本信息</CardTitle>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleUpdateProfile" class="space-y-4 max-w-lg">
          <div class="grid gap-2">
            <label class="text-sm font-medium">用户名</label>
            <Input v-model="form.username" disabled />
            <p class="text-xs text-muted-foreground">用户名不可修改</p>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">邮箱</label>
            <Input v-model="form.email" />
          </div>

          <div class="pt-4">
            <Button type="submit" :disabled="loading" class="gap-2">
              <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
              保存修改
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>修改密码</CardTitle>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleChangePassword" class="space-y-4 max-w-lg">
          <div class="grid gap-2">
            <label class="text-sm font-medium">旧密码</label>
            <Input v-model="pwdForm.old_password" type="password" autocomplete="current-password" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">新密码</label>
            <Input v-model="pwdForm.new_password" type="password" autocomplete="new-password" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">确认新密码</label>
            <Input v-model="pwdForm.confirm_password" type="password" autocomplete="new-password" />
          </div>

          <div class="pt-4">
            <Button type="submit" variant="secondary" :disabled="pwdLoading" class="gap-2">
              <Loader2 v-if="pwdLoading" class="h-4 w-4 animate-spin" />
              修改密码
            </Button>
            <p class="mt-2 text-xs text-muted-foreground">修改成功后将自动退出登录，请使用新密码重新登录。</p>
          </div>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { ElMessage } from '@/lib/element'
import { userApi } from '@/api/user'
import { Loader2 } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

const userStore = useUserStore()
const router = useRouter()
const loading = ref(false)
const pwdLoading = ref(false)

const form = reactive({
  username: '',
  email: ''
})

const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

onMounted(() => {
  if (userStore.user) {
    form.username = userStore.user.username
    form.email = userStore.user.email
  }
})

const handleUpdateProfile = async () => {
  loading.value = true
  try {
    await userApi.updateProfile({ email: form.email })
    ElMessage.success('保存成功')
    await userStore.checkAuth()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleChangePassword = async () => {
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    ElMessage.error('两次输入的密码不一致')
    return
  }

  pwdLoading.value = true
  try {
    await userApi.changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password
    })
    ElMessage.success('密码修改成功，请重新登录')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''

    await userStore.logout()
    router.push({ name: 'Login' })
  } catch (error) {
    console.error(error)
  } finally {
    pwdLoading.value = false
  }
}
</script>
