<template>
  <div class="min-h-screen bg-muted/30 text-foreground">
    <header class="sticky top-0 z-30 h-16 bg-background/80 backdrop-blur border-b border-border">
      <div class="mx-auto max-w-7xl h-full px-4 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3 min-w-0">
          <Button
            variant="outline"
            size="icon-sm"
            class="bg-muted/30"
            @click="toggleSidebar"
          >
            <PanelLeftClose v-if="!sidebarCollapsed" class="h-4 w-4" />
            <PanelLeftOpen v-else class="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="sm"
            class="hidden sm:inline-flex"
            @click="router.push('/zones')"
          >
            <ChevronLeft class="h-4 w-4" />
            返回专区
          </Button>

          <div class="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <Sparkles class="h-5 w-5" />
          </div>

          <div class="min-w-0">
            <div class="text-sm font-semibold leading-none">Google 业务专区</div>
            <div class="mt-1 text-xs text-muted-foreground truncate">学生优惠订阅自动化处理平台</div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <div class="hidden sm:flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1.5">
            <Wallet class="h-4 w-4 text-muted-foreground" />
            <span class="text-xs text-muted-foreground">余额</span>
            <span class="text-sm font-semibold text-foreground">¥{{ userBalance }}</span>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button type="button" variant="default" size="sm" class="gap-2">
                <UserRound class="h-4 w-4" />
                <span class="max-w-[140px] truncate">{{ userStore.user?.username || 'User' }}</span>
                <ChevronDown class="h-4 w-4 opacity-70" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" class="w-44">
              <DropdownMenuItem @select="handleCommand('profile')">个人信息</DropdownMenuItem>
              <DropdownMenuItem @select="handleCommand('recharge')">充值</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-destructive" @select="handleCommand('logout')">退出登录</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>

    <div
      v-if="!sidebarCollapsed"
      class="md:hidden fixed inset-0 z-30 bg-black/30"
      @click="toggleSidebar"
    />

    <!-- Main -->
    <div class="flex min-h-[calc(100vh-4rem)]">
      <aside
        class="fixed md:static top-16 bottom-0 left-0 z-40 bg-card text-card-foreground border-r border-border shadow-sm md:shadow-none transition-all duration-200 overflow-hidden"
        :class="sidebarCollapsed ? '-translate-x-full md:translate-x-0 md:w-16 w-64' : 'translate-x-0 w-64 md:w-64'"
      >
        <nav class="h-full px-2 py-4 space-y-1">
          <Button
            variant="ghost"
            class="w-full h-11 px-3 gap-2"
            :class="[
              sidebarCollapsed ? 'justify-center px-2' : 'justify-start',
              activeModule === 'workstation' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
            ]"
            @click="handleModuleChange('workstation')"
          >
            <LayoutDashboard class="h-4 w-4 shrink-0" />
            <span v-if="!sidebarCollapsed" class="flex-1 text-left">工作台</span>

            <div v-if="!sidebarCollapsed" class="ml-auto flex items-center gap-2">
              <span
                class="h-2 w-2 rounded-full"
                :class="browserStatus?.engine_online ? 'bg-emerald-500' : 'bg-red-500'"
                :title="browserStatus?.engine_online ? '引擎在线' : '引擎离线'"
              />
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md border border-border bg-muted/30 hover:bg-muted transition-colors"
                :class="isBrowserStatusLoading ? 'opacity-70' : ''"
                :title="isBrowserStatusLoading ? '刷新中...' : '刷新浏览器状态'"
                @click.stop="fetchBrowserStatus"
              >
                <RefreshCcw v-if="!isBrowserStatusLoading" class="h-4 w-4 text-muted-foreground" />
                <Loader2 v-else class="h-4 w-4 text-primary animate-spin" />
              </button>
            </div>
          </Button>

          <Button
            variant="ghost"
            class="w-full h-11 px-3 gap-2"
            :class="[
              sidebarCollapsed ? 'justify-center px-2' : 'justify-start',
              activeModule === 'accounts' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
            ]"
            @click="handleModuleChange('accounts')"
          >
            <Users class="h-4 w-4 shrink-0" />
            <span v-if="!sidebarCollapsed" class="text-left">谷歌账号管理</span>
          </Button>

          <Button
            variant="ghost"
            class="w-full h-11 px-3 gap-2"
            :class="[
              sidebarCollapsed ? 'justify-center px-2' : 'justify-start',
              activeModule === 'proxy-management' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
            ]"
            @click="handleModuleChange('proxy-management')"
          >
            <Network class="h-4 w-4 shrink-0" />
            <span v-if="!sidebarCollapsed" class="text-left">代理管理</span>
          </Button>
        </nav>
      </aside>

      <main class="flex-1 min-w-0 bg-muted/20 p-4 sm:p-6 md:ml-0">
        <div class="max-w-7xl mx-auto">
          <div class="min-w-0 overflow-x-auto">
            <component :is="currentModuleComponent" />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { balanceApi } from '@/api/balance'
import {
  ChevronDown,
  ChevronLeft,
  LayoutDashboard,
  Loader2,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCcw,
  Sparkles,
  UserRound,
  Users,
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
import { googleBrowserApi } from '@/api/google'

// 导入模块组件
import WorkstationModule from './google-modules/WorkstationModule.vue'
import GoogleAccountsModule from './google-modules/GoogleAccountsModule.vue'
import ProxyManagementModule from './google-modules/ProxyManagementModule.vue'

const router = useRouter()
const userStore = useUserStore()

// 侧边栏状态
const sidebarCollapsed = ref(false)
const activeModule = ref('workstation')

// 浏览器状态
const browserStatus = ref<any>(null)
const isBrowserStatusLoading = ref(false)

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

// 用户余额（从余额API/用户信息获取）
const userBalance = ref('0.00')

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

// 模块组件映射
const moduleComponents: Record<string, any> = {
  workstation: WorkstationModule,
  accounts: GoogleAccountsModule,
  'proxy-management': ProxyManagementModule
}

// 当前模块组件
const currentModuleComponent = shallowRef(WorkstationModule)

// 切换侧边栏
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 切换模块
const handleModuleChange = (index: string) => {
  activeModule.value = index
  currentModuleComponent.value = moduleComponents[index] || WorkstationModule
}

// 处理用户菜单命令
const handleCommand = (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'recharge':
      router.push('/recharge')
      break
    case 'logout':
      userStore.logout()
      router.push('/login')
      break
  }
}

// 组件挂载时获取用户信息（包括余额）
onMounted(async () => {
  // 确保用户信息是最新的
  await userStore.fetchUserProfile()
  // 并行加载
  await Promise.all([
    refreshBalance(),
    fetchBrowserStatus()
  ])
})
</script>

