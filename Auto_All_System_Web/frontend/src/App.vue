<template>
  <router-view />
  <Toaster />
  <MessageBoxHost />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { Toaster } from '@/components/ui/toast'
import MessageBoxHost from '@/components/app/MessageBoxHost.vue'

const userStore = useUserStore()

onMounted(() => {
  // 初始化时检查登录状态
  userStore.checkAuth()
})
</script>
