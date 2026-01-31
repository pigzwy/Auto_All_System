<template>
  <div class="flex h-screen w-full bg-muted/30 text-foreground">
    <!-- 侧边栏 -->
    <aside
      class="flex flex-col bg-slate-950 text-slate-100 border-r border-slate-900 shadow-lg transition-all duration-200"
      :class="isSidebarCollapsed ? 'w-16' : 'w-[240px]'"
    >
      <div class="h-16 px-4 border-b border-slate-900/80 flex items-center justify-center">
        <div class="flex items-center gap-3" :class="isSidebarCollapsed ? 'justify-center' : 'justify-start'">
          <div class="h-9 w-9 rounded-lg bg-indigo-500/20 text-indigo-200 flex items-center justify-center">
            <Setting class="h-5 w-5" />
          </div>
          <div v-if="!isSidebarCollapsed" class="font-semibold tracking-wide">管理后台</div>
        </div>
      </div>

      <nav class="flex-1 overflow-y-auto py-4">
        <div class="px-2">
          <RouterLink
            to="/admin"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin') && !isPathActive('/admin/google-business')
                ? 'bg-slate-900/70 text-white'
                : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <HomeFilled class="h-4 w-4 shrink-0" :class="isPathActive('/admin') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">控制台</span>
          </RouterLink>
        </div>

        <div v-if="!isSidebarCollapsed" class="mt-6 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          用户管理
        </div>
        <div class="px-2">
          <RouterLink
            to="/admin/users"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/users') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <User class="h-4 w-4 shrink-0" :class="isPathActive('/admin/users') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">用户列表</span>
          </RouterLink>

          <RouterLink
            to="/admin/user-balance"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/user-balance') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Wallet class="h-4 w-4 shrink-0" :class="isPathActive('/admin/user-balance') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">用户余额</span>
          </RouterLink>

          <RouterLink
            to="/admin/activity-log"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/activity-log') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <List class="h-4 w-4 shrink-0" :class="isPathActive('/admin/activity-log') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">操作日志</span>
          </RouterLink>
        </div>

        <div v-if="!isSidebarCollapsed" class="mt-6 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          业务管理
        </div>
        <div class="px-2">
          <RouterLink
            to="/admin/zones"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/zones') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Grid class="h-4 w-4 shrink-0" :class="isPathActive('/admin/zones') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">专区管理</span>
          </RouterLink>
          <RouterLink
            to="/admin/tasks"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/tasks') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <List class="h-4 w-4 shrink-0" :class="isPathActive('/admin/tasks') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">任务管理</span>
          </RouterLink>
          <RouterLink
            to="/admin/cards"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/cards') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <CreditCard class="h-4 w-4 shrink-0" :class="isPathActive('/admin/cards') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">虚拟卡管理</span>
          </RouterLink>
        </div>

        <div v-if="!isSidebarCollapsed" class="mt-6 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          财务管理
        </div>
        <div class="px-2">
          <RouterLink
            to="/admin/orders"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/orders') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Money class="h-4 w-4 shrink-0" :class="isPathActive('/admin/orders') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">订单管理</span>
          </RouterLink>
          <RouterLink
            to="/admin/recharge-cards"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/recharge-cards') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Tickets class="h-4 w-4 shrink-0" :class="isPathActive('/admin/recharge-cards') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">充值卡密</span>
          </RouterLink>
          <RouterLink
            to="/admin/payment-configs"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/payment-configs') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Setting class="h-4 w-4 shrink-0" :class="isPathActive('/admin/payment-configs') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">支付配置</span>
          </RouterLink>
        </div>

        <div v-if="!isSidebarCollapsed" class="mt-6 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          集成管理
        </div>
        <div class="px-2">
          <RouterLink
            to="/admin/google-accounts"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/google-accounts') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <UserFilled class="h-4 w-4 shrink-0" :class="isPathActive('/admin/google-accounts') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">Google账号</span>
          </RouterLink>
          <RouterLink
            to="/admin/proxy"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/proxy') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Connection class="h-4 w-4 shrink-0" :class="isPathActive('/admin/proxy') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">代理配置</span>
          </RouterLink>
          <RouterLink
            to="/admin/bitbrowser"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/bitbrowser') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Grid class="h-4 w-4 shrink-0" :class="isPathActive('/admin/bitbrowser') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">比特浏览器</span>
          </RouterLink>
          <RouterLink
            to="/admin/geekez"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/geekez') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Grid class="h-4 w-4 shrink-0" :class="isPathActive('/admin/geekez') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">Geekez浏览器</span>
          </RouterLink>
          <RouterLink
            to="/admin/email"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/email') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Mail class="h-4 w-4 shrink-0" :class="isPathActive('/admin/email') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">域名邮箱</span>
          </RouterLink>
        </div>

        <div v-if="!isSidebarCollapsed" class="mt-6 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          系统
        </div>
        <div class="px-2">
          <RouterLink
            to="/admin/analytics"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/analytics') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <DataAnalysis class="h-4 w-4 shrink-0" :class="isPathActive('/admin/analytics') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">数据分析</span>
          </RouterLink>
          <RouterLink
            to="/admin/plugins"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/plugins') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Box class="h-4 w-4 shrink-0" :class="isPathActive('/admin/plugins') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">插件管理</span>
          </RouterLink>
          <RouterLink
            to="/admin/settings"
            class="group mx-2 my-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors"
            :class="[
              isPathActive('/admin/settings') ? 'bg-slate-900/70 text-white' : 'text-slate-300 hover:bg-slate-900/60 hover:text-white',
              isSidebarCollapsed ? 'justify-center' : 'justify-start'
            ]"
          >
            <Setting class="h-4 w-4 shrink-0" :class="isPathActive('/admin/settings') ? 'text-blue-400' : 'text-slate-400'" />
            <span v-if="!isSidebarCollapsed">系统设置</span>
          </RouterLink>
        </div>
      </nav>
    </aside>

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="h-16 bg-background border-b border-border flex items-center justify-between px-6 shadow-sm">
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
            <RouterLink to="/admin" class="text-muted-foreground hover:text-foreground">管理后台</RouterLink>
            <span v-if="currentRouteName" class="text-muted-foreground">/</span>
            <span v-if="currentRouteName" class="font-medium text-foreground">{{ currentRouteName }}</span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <button type="button" class="relative flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted">
            <Bell class="h-4 w-4" />
            <span class="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500" />
          </button>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <button type="button" class="flex items-center gap-2 rounded-lg px-2 py-1 transition-colors hover:bg-muted">
                <Avatar size="sm" class="h-8 w-8 bg-slate-100 text-slate-700 border border-slate-200">
                  <AvatarImage v-if="userStore.user?.avatar" :src="userStore.user.avatar" alt="" />
                  <AvatarFallback class="bg-slate-100 text-slate-700">{{ userStore.user?.username?.[0]?.toUpperCase() }}</AvatarFallback>
                </Avatar>
                <span class="hidden md:inline text-sm font-medium text-slate-700">{{ userStore.user?.username }}</span>
                <ArrowDown class="h-4 w-4 text-slate-400" />
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" class="w-56">
              <DropdownMenuLabel>
                <div class="text-sm font-bold text-foreground">管理员</div>
                <div class="mt-0.5 text-xs text-muted-foreground">{{ userStore.user?.email }}</div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem @select="handleCommand('profile')">个人设置</DropdownMenuItem>
              <DropdownMenuItem @select="handleCommand('user-portal')">返回用户端</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-rose-600 focus:text-rose-600" @select="handleCommand('logout')">退出登录</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <main class="flex-1 overflow-auto !p-6 bg-muted/20">
        <div class="max-w-7xl mx-auto">
          <router-view />
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
  Setting,
  HomeFilled,
  User,
  Grid,
  Wallet,
  Connection,
  DataAnalysis,
  Bell,
  ArrowDown,
  Box,
  Fold,
  Expand,
  Money,
  CreditCard,
  UserFilled,
  Tickets,
  Mail,
  List,
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

const currentRouteName = computed(() => {
  const nameMap: Record<string, string> = {
    'AdminDashboard': '控制台',
    'AdminUsers': '用户管理',
    'AdminTasks': '任务管理',
    'AdminCards': '虚拟卡管理',
    'AdminPlugins': '插件管理',
    'AdminBitbrowser': '比特浏览器',
    'AdminGeekez': 'Geekez浏览器',
  }
  return nameMap[route.name as string] || ''
})

const isPathActive = (path: string) => {
  if (path === '/admin') return route.path === '/admin'
  return route.path === path || route.path.startsWith(`${path}/`)
}

const handleCommand = async (command: string) => {
  switch (command) {
    case 'logout':
      try {
        await userStore.logout()
        ElMessage.success('退出成功')
        router.push({ name: 'Login' })
      } catch (error) {
        console.error('Logout error:', error)
      }
      break
    case 'profile':
      router.push({ name: 'Profile' })
      break
    case 'user-portal':
      router.push({ name: 'Dashboard' })
      break
  }
}
</script>
