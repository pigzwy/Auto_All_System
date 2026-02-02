<template>
  <header class="sticky top-0 z-30 border-b border-border/50 bg-background/80 backdrop-blur-xl">
    <div class="mx-auto max-w-[1600px] px-6">
      <!-- 主导航行 -->
      <div class="flex h-14 items-center justify-between gap-4">
        <!-- 左侧：返回 + 专区切换 -->
        <div class="flex items-center gap-4">
          <Button variant="ghost" size="sm" class="gap-2 text-muted-foreground hover:text-foreground" @click="router.push('/zones')">
            <ChevronLeft class="h-4 w-4" />
            <span class="hidden sm:inline">返回专区</span>
          </Button>
          <div class="h-6 w-px bg-border" />
          <ZoneSwitcher />
        </div>

        <!-- 右侧：引擎状态 + 余额 + 用户菜单 -->
        <div class="flex items-center gap-3">
          <!-- 浏览器引擎状态 -->
          <div class="hidden sm:flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1">
            <span
              class="h-2 w-2 rounded-full"
              :class="browserStatus?.engine_online ? 'bg-emerald-500' : 'bg-red-500'"
            />
            <span class="text-xs text-muted-foreground">
              {{ browserStatus?.engine_online ? '引擎在线' : '引擎离线' }}
            </span>
            <button
              class="ml-1 rounded p-0.5 hover:bg-muted"
              :disabled="isBrowserStatusLoading"
              @click="fetchBrowserStatus"
            >
              <RefreshCcw v-if="!isBrowserStatusLoading" class="h-3 w-3 text-muted-foreground" />
              <Loader2 v-else class="h-3 w-3 animate-spin text-muted-foreground" />
            </button>
          </div>

          <!-- 余额 -->
          <div class="hidden sm:flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1.5">
            <Wallet class="h-4 w-4 text-muted-foreground" />
            <span class="text-xs text-muted-foreground">余额</span>
            <span class="text-sm font-semibold text-foreground">¥{{ userBalance }}</span>
          </div>

          <!-- 用户菜单 -->
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="sm" class="gap-2">
                <div class="flex h-7 w-7 items-center justify-center rounded-full bg-muted">
                  <UserRound class="h-4 w-4 text-muted-foreground" />
                </div>
                <span class="hidden text-sm sm:inline">{{ userStore.user?.username || '用户' }}</span>
                <ChevronDown class="h-4 w-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" class="w-48">
              <DropdownMenuItem @select="router.push('/profile')">
                <UserRound class="mr-2 h-4 w-4" />
                个人资料
              </DropdownMenuItem>
              <DropdownMenuItem @select="router.push('/recharge')">
                <Wallet class="mr-2 h-4 w-4" />
                充值
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-destructive" @select="handleLogout">
                <LogOut class="mr-2 h-4 w-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <!-- 功能操作栏插槽 -->
      <div v-if="$slots.toolbar" class="flex flex-wrap items-center gap-4 border-t border-border/30 py-3">
        <slot name="toolbar" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { balanceApi } from '@/api/balance'
import { googleBrowserApi } from '@/api/google'
import {
  ChevronDown,
  ChevronLeft,
  Loader2,
  LogOut,
  RefreshCcw,
  UserRound,
  Wallet,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import ZoneSwitcher from './ZoneSwitcher.vue'

const router = useRouter()
const userStore = useUserStore()

const browserStatus = ref<any>(null)
const isBrowserStatusLoading = ref(false)
const userBalance = ref('0.00')

const fetchBrowserStatus = async () => {
  isBrowserStatusLoading.value = true
  try {
    const res = await googleBrowserApi.getStatus()
    browserStatus.value = res
  } catch (error) {
    console.error('Failed to fetch browser status', error)
  } finally {
    isBrowserStatusLoading.value = false
  }
}

const refreshBalance = async () => {
  if (userStore.user && 'balance' in userStore.user) {
    userBalance.value = (userStore.user as any).balance || '0.00'
  }
  try {
    const balance = await balanceApi.getMyBalance()
    userBalance.value = String(balance.balance || '0.00')
  } catch {
    // 保留已有余额显示
  }
}

const handleLogout = async () => {
  await userStore.logout()
  router.replace('/login')
}

onMounted(async () => {
  await userStore.fetchUserProfile()
  await Promise.all([
    refreshBalance(),
    fetchBrowserStatus()
  ])
})
</script>
