<template>
  <div class="flex h-screen w-full bg-muted/30 text-foreground">
    <!-- 侧边栏 -->
    <aside
      class="flex flex-col bg-slate-950 text-slate-100 shadow-lg transition-all duration-200"
      :class="isSidebarCollapsed ? 'w-16' : 'w-64'"
    >
      <!-- Logo -->
      <div class="flex h-16 items-center justify-center border-b border-slate-900/80">
        <div class="flex items-center gap-2 font-bold tracking-wide" :class="isSidebarCollapsed ? 'text-base' : 'text-xl'">
          <span class="text-blue-500" :class="isSidebarCollapsed ? 'text-xl' : 'text-2xl'">⚡</span>
          <span v-if="!isSidebarCollapsed">Auto All</span>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="flex-1 overflow-y-auto py-4">
        <div class="px-2">
          <RouterLink
            to="/"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <HomeFilled class="h-4 w-4 shrink-0" :class="isPathActive('/') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed" class="group-hover:text-white transition-colors">首页</span>
          </RouterLink>
        </div>

        <div v-if="!isSidebarCollapsed" class="mt-6 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          业务管理
        </div>
        <div class="px-2">
          <RouterLink
            to="/zones"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/zones') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Grid class="h-4 w-4 shrink-0" :class="isPathActive('/zones') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed" class="group-hover:text-white transition-colors">专区管理</span>
          </RouterLink>

          <RouterLink
            to="/cards"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/cards') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <CreditCard class="h-4 w-4 shrink-0" :class="isPathActive('/cards') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed" class="group-hover:text-white transition-colors">虚拟卡</span>
          </RouterLink>
        </div>

        <div v-if="!isSidebarCollapsed" class="mt-6 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          账户 & 设置
        </div>
        <div class="px-2">
          <RouterLink
            to="/balance"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/balance') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Wallet class="h-4 w-4 shrink-0" :class="isPathActive('/balance') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed" class="group-hover:text-white transition-colors">余额管理</span>
          </RouterLink>

          <RouterLink
            to="/recharge"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/recharge') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Money class="h-4 w-4 shrink-0" :class="isPathActive('/recharge') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed" class="group-hover:text-white transition-colors">账户充值</span>
          </RouterLink>

          <RouterLink
            to="/vip"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/vip') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Star class="h-4 w-4 shrink-0" :class="isPathActive('/vip') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed" class="group-hover:text-white transition-colors">VIP会员</span>
          </RouterLink>

          <RouterLink
            to="/profile"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/profile') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <User class="h-4 w-4 shrink-0" :class="isPathActive('/profile') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed" class="group-hover:text-white transition-colors">个人中心</span>
          </RouterLink>

          <RouterLink
            v-if="userStore.user?.is_staff"
            to="/admin"
            class="mx-2 my-1 mt-6 flex items-center gap-3 rounded-lg bg-gradient-to-r from-indigo-500 to-fuchsia-500 px-3 py-2 text-sm font-bold text-white shadow-sm shadow-indigo-500/20 transition-colors hover:from-indigo-400 hover:to-fuchsia-400"
            :class="isSidebarCollapsed ? 'justify-center' : 'justify-start'"
          >
            <Setting class="h-4 w-4 shrink-0" />
            <span v-if="!isSidebarCollapsed">管理后台</span>
          </RouterLink>
        </div>
      </nav>
      
      <!-- 用户简略信息 (底部) -->
      <div class="border-t border-slate-900/80 bg-slate-950/60 p-4">
        <div class="flex items-center" :class="isSidebarCollapsed ? 'justify-center' : 'gap-3'">
          <Avatar size="sm" class="h-8 w-8 bg-blue-600 text-white">
            <AvatarImage v-if="userStore.user?.avatar" :src="userStore.user.avatar" alt="" />
            <AvatarFallback class="bg-blue-600 text-white">{{ userStore.user?.username?.[0]?.toUpperCase() }}</AvatarFallback>
          </Avatar>
          <div v-if="!isSidebarCollapsed" class="flex flex-col overflow-hidden">
            <span class="text-sm font-medium text-white truncate">{{ userStore.user?.username }}</span>
            <span class="text-xs text-slate-400 truncate">VIP {{ userStore.user?.vip_level || 0 }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部导航栏 -->
      <header class="h-16 bg-background border-b border-border flex items-center justify-between px-6 shadow-sm z-10">
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background text-muted-foreground transition-colors hover:bg-muted"
            @click="isSidebarCollapsed = !isSidebarCollapsed"
            :title="isSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
          >
            <Fold v-if="!isSidebarCollapsed" class="h-4 w-4" />
            <Expand v-else class="h-4 w-4" />
          </button>

          <div class="flex items-center gap-2 text-sm">
            <RouterLink to="/" class="text-muted-foreground hover:text-foreground">首页</RouterLink>
            <span v-if="currentRouteName" class="text-muted-foreground">/</span>
            <span v-if="currentRouteName" class="font-medium text-foreground">{{ currentRouteName }}</span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <!-- 通知铃铛 (示例) -->
          <button type="button" class="relative flex h-8 w-8 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted">
            <Bell class="h-4 w-4" />
            <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>

          </button>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <button
                type="button"
                class="flex items-center gap-2 rounded-lg px-2 py-1 transition-colors hover:bg-muted"
              >
                <Avatar size="sm" class="h-8 w-8 bg-blue-100 text-blue-600 border border-blue-200">
                  <AvatarImage v-if="userStore.user?.avatar" :src="userStore.user.avatar" alt="" />
                  <AvatarFallback class="bg-blue-100 text-blue-600">{{ userStore.user?.username?.[0]?.toUpperCase() }}</AvatarFallback>
                </Avatar>
                <div class="hidden md:flex flex-col items-start">
                  <span class="text-sm font-medium text-gray-700 leading-none">{{ userStore.user?.username }}</span>
                  <span class="mt-1 text-xs text-gray-400">余额: ¥{{ userStore.user?.balance || '0.00' }}</span>
                </div>
                <ArrowDown class="h-4 w-4 text-gray-400" />
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" class="w-56">
              <DropdownMenuLabel>
                <div class="text-sm font-bold text-foreground">我的账户</div>
                <div class="mt-0.5 text-xs text-muted-foreground">{{ userStore.user?.email }}</div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem @select="handleCommand('profile')">
                <User class="h-4 w-4" />
                个人中心
              </DropdownMenuItem>
              <DropdownMenuItem v-if="userStore.user?.is_staff" @select="handleCommand('admin')">
                <Setting class="h-4 w-4" />
                管理后台
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-rose-600 focus:text-rose-600" @select="handleCommand('logout')">
                <SwitchButton class="h-4 w-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <!-- 内容区域 -->
      <main class="flex-1 overflow-auto bg-muted/20 p-6">
        <div class="max-w-7xl mx-auto">
          <router-view v-slot="{ Component }">
            <Transition
              mode="out-in"
              enter-active-class="transition duration-200 ease-out"
              enter-from-class="opacity-0 translate-y-2"
              enter-to-class="opacity-100 translate-y-0"
              leave-active-class="transition duration-150 ease-in"
              leave-from-class="opacity-100 translate-y-0"
              leave-to-class="opacity-0 -translate-y-2"
            >
              <component :is="Component" />
            </Transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from '@/lib/element'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { 
  Setting, Money, Star, HomeFilled, Grid, CreditCard, 
  Wallet, User, ArrowDown, Bell, SwitchButton, Fold, Expand
} from '@/icons'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isSidebarCollapsed = ref(false)

let sidebarMq: MediaQueryList | null = null
const syncSidebarCollapse = () => {
  if (!sidebarMq) return
  isSidebarCollapsed.value = sidebarMq.matches
}

onMounted(() => {
  sidebarMq = window.matchMedia('(max-width: 767px)')
  syncSidebarCollapse()
  sidebarMq.addEventListener('change', syncSidebarCollapse)
})

onBeforeUnmount(() => {
  sidebarMq?.removeEventListener('change', syncSidebarCollapse)
})

const currentRouteName = computed(() => route.meta?.title || route.name as string)

const isPathActive = (path: string) => {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await userStore.logout()
      ElMessage.success('退出成功')
      router.push({ name: 'Login' })
    } catch (error) {
      console.error('Logout error:', error)
    }
  } else if (command === 'profile') {
    router.push({ name: 'Profile' })
  } else if (command === 'admin') {
    router.push({ name: 'AdminDashboard' })
  }
}
</script>
