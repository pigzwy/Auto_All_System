<template>
  <div class="min-h-screen bg-gradient-to-b from-background to-muted/30 text-foreground">
    <!-- 顶部导航栏 -->
    <header class="sticky top-0 z-30 border-b border-border/50 bg-background/80 backdrop-blur-xl">
      <div class="mx-auto max-w-[1600px] px-6">
        <!-- 主导航行 -->
        <div class="flex h-14 items-center justify-between gap-4">
          <!-- 左侧：返回 + 标题 -->
          <div class="flex items-center gap-4">
            <Button variant="ghost" size="sm" class="gap-2 text-muted-foreground hover:text-foreground" @click="router.push('/zones')">
              <ChevronLeft class="h-4 w-4" />
              <span class="hidden sm:inline">返回专区</span>
            </Button>
            <div class="h-6 w-px bg-border" />
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                <Sparkles class="h-4 w-4 text-primary" />
              </div>
              <h1 class="text-base font-semibold">Google 业务专区</h1>
            </div>
            
            <!-- 浏览器状态 -->
            <div class="flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1">
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
          </div>

          <!-- 右侧：余额 + 用户菜单 -->
          <div class="flex items-center gap-3">
            <div class="hidden sm:flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1.5">
              <Wallet class="h-4 w-4 text-muted-foreground" />
              <span class="text-xs text-muted-foreground">余额</span>
              <span class="text-sm font-semibold text-foreground">¥{{ userBalance }}</span>
            </div>

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
                <DropdownMenuItem @select="handleCommand('profile')">
                  <UserRound class="mr-2 h-4 w-4" />
                  个人资料
                </DropdownMenuItem>
                <DropdownMenuItem @select="handleCommand('recharge')">
                  <Wallet class="mr-2 h-4 w-4" />
                  充值
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem class="text-destructive" @select="handleCommand('logout')">
                  <LogOut class="mr-2 h-4 w-4" />
                  退出登录
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <!-- 功能操作栏 -->
        <div class="flex flex-wrap items-center gap-4 border-t border-border/30 py-3">
          <!-- 基础操作 -->
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" class="gap-2" :disabled="loading" @click="refreshAccounts">
              <RefreshCcw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
              刷新
            </Button>
            <Button size="sm" class="gap-2" @click="openAddDialog">
              <Plus class="h-4 w-4" />
              添加账号
            </Button>
            <Button variant="secondary" size="sm" class="gap-2" @click="openImportDialog">
              <Upload class="h-4 w-4" />
              批量导入
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="sm" class="gap-2">
                  <Download class="h-4 w-4" />
                  导出
                  <ChevronDown class="h-4 w-4 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="w-36">
                <DropdownMenuItem @select="handleExport('csv')">导出 CSV</DropdownMenuItem>
                <DropdownMenuItem @select="handleExport('txt')">导出 TXT</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 已选账号 -->
          <div class="flex items-center gap-3">
            <span class="text-sm text-muted-foreground">已选：</span>
            <div v-if="selectedCount > 0" class="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-1.5">
              <div class="h-2 w-2 rounded-full bg-primary animate-pulse" />
              <span class="text-sm font-medium text-primary">{{ selectedCount }} 个账号</span>
              <button class="ml-1 rounded p-0.5 hover:bg-primary/20" @click="clearSelection">
                <X class="h-3.5 w-3.5 text-primary/70 hover:text-primary" />
              </button>
            </div>
            <span v-else class="text-sm italic text-muted-foreground/60">勾选表格行选择账号</span>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 自动化操作组 -->
          <div class="flex items-center gap-1.5">
            <span class="mr-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">自动化</span>
            <Button size="sm" class="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white" :disabled="selectedCount === 0" @click="openOneClickDialog">
              <Wand2 class="h-4 w-4" />
              一键全自动
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="secondary" size="sm" class="gap-2 bg-blue-600 hover:bg-blue-700 text-white" :disabled="selectedCount === 0">
                  <CreditCard class="h-4 w-4" />
                  验证/绑卡
                  <ChevronDown class="h-4 w-4 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="w-44">
                <DropdownMenuItem @select="handleBatchCommand('sheerid')">SheerID 验证</DropdownMenuItem>
                <DropdownMenuItem @select="handleBatchCommand('bind_card')">自动绑卡</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="secondary" size="sm" class="gap-2 bg-violet-600 hover:bg-violet-700 text-white" :disabled="selectedCount === 0">
                  <Shield class="h-4 w-4" />
                  安全设置
                  <ChevronDown class="h-4 w-4 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="w-44">
                <DropdownMenuItem @select="handleSecurityCommand('change_2fa')">修改 2FA</DropdownMenuItem>
                <DropdownMenuItem @select="handleSecurityCommand('change_recovery')">修改辅助邮箱</DropdownMenuItem>
                <DropdownMenuItem @select="handleSecurityCommand('get_backup_codes')">获取备份码</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem @select="handleSecurityCommand('one_click_update')">一键安全更新</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="sm" class="gap-2 border-sky-500/50 text-sky-600 hover:bg-sky-50 hover:text-sky-700 dark:text-sky-400 dark:hover:bg-sky-950" :disabled="selectedCount === 0">
                  <Monitor class="h-4 w-4" />
                  订阅管理
                  <ChevronDown class="h-4 w-4 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="w-44">
                <DropdownMenuItem @select="handleSubscriptionCommand('verify_status')">验证订阅状态</DropdownMenuItem>
                <DropdownMenuItem @select="handleSubscriptionCommand('click_subscribe')">点击订阅按钮</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 单个账号操作 -->
          <div class="flex items-center gap-1.5">
            <span class="mr-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">管理</span>
            <Button variant="outline" size="sm" class="gap-2 border-teal-500/50 text-teal-600 hover:bg-teal-50 hover:text-teal-700 dark:text-teal-400 dark:hover:bg-teal-950" :disabled="selectedCount !== 1" @click="handleLaunchGeekez">
              <ExternalLink class="h-4 w-4" />
              {{ geekezActionLabel }}
            </Button>
            <Button variant="outline" size="sm" class="gap-2 border-orange-500/50 text-orange-600 hover:bg-orange-50 hover:text-orange-700 dark:text-orange-400 dark:hover:bg-orange-950" :disabled="selectedCount !== 1" @click="handleEdit">
              <Edit3 class="h-4 w-4" />
              编辑
            </Button>
            <Button variant="outline" size="sm" class="gap-2 border-slate-500/50 text-slate-600 hover:bg-slate-50 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-900" :disabled="selectedCount !== 1" @click="handleViewTasks">
              <FileText class="h-4 w-4" />
              日志
            </Button>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 删除 -->
          <Button variant="outline" size="sm" class="gap-2 border-red-500/50 text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-950" :disabled="selectedCount === 0" @click="handleBulkDelete">
            <Trash2 class="h-4 w-4" />
            批量删除
          </Button>
        </div>
      </div>
    </header>

    <!-- 主内容区：直接铺开 -->
    <main class="mx-auto max-w-[1600px] p-6">
      <GoogleAccountsModule ref="accountsModuleRef" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, provide, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { balanceApi } from '@/api/balance'
import {
  ChevronDown,
  ChevronLeft,
  CreditCard,
  Download,
  Edit3,
  ExternalLink,
  FileText,
  Loader2,
  LogOut,
  Monitor,
  Plus,
  RefreshCcw,
  Shield,
  Sparkles,
  Trash2,
  Upload,
  UserRound,
  Wallet,
  Wand2,
  X,
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

import GoogleAccountsModule from './google-modules/GoogleAccountsModule.vue'

const router = useRouter()
const userStore = useUserStore()

// ========== 账号模块引用 ==========
const accountsModuleRef = ref<InstanceType<typeof GoogleAccountsModule> | null>(null)

// ========== 状态 ==========
const loading = ref(false)
const selectedCount = ref(0)

// 浏览器状态
const browserStatus = ref<any>(null)
const isBrowserStatusLoading = ref(false)

// 用户余额
const userBalance = ref('0.00')

// 当前选中的单个账号（用于单账号操作）
const selectedAccount = ref<any>(null)

// 根据环境状态显示按钮文字
const geekezActionLabel = computed(() => {
  if (!selectedAccount.value) return '打开环境'
  return selectedAccount.value.geekez_profile_exists ? '打开环境' : '创建环境'
})

// 提供给子组件
provide('loading', loading)
provide('selectedCount', selectedCount)

// ========== 方法 ==========
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

const refreshAccounts = () => {
  window.dispatchEvent(new CustomEvent('google-accounts-refresh'))
}

const openAddDialog = () => {
  window.dispatchEvent(new CustomEvent('google-open-add-dialog'))
}

const openImportDialog = () => {
  window.dispatchEvent(new CustomEvent('google-open-import-dialog'))
}

const openOneClickDialog = () => {
  window.dispatchEvent(new CustomEvent('google-open-oneclick-dialog'))
}

const clearSelection = () => {
  window.dispatchEvent(new CustomEvent('google-clear-selection'))
}

const handleExport = (format: string) => {
  window.dispatchEvent(new CustomEvent('google-export', { detail: format }))
}

const handleBatchCommand = (command: string) => {
  window.dispatchEvent(new CustomEvent('google-batch-command', { detail: command }))
}

const handleSecurityCommand = (command: string) => {
  window.dispatchEvent(new CustomEvent('google-security-command', { detail: command }))
}

const handleSubscriptionCommand = (command: string) => {
  window.dispatchEvent(new CustomEvent('google-subscription-command', { detail: command }))
}

const handleBulkDelete = () => {
  window.dispatchEvent(new CustomEvent('google-bulk-delete'))
}

// 单个账号操作
const handleLaunchGeekez = () => {
  window.dispatchEvent(new CustomEvent('google-launch-geekez'))
}

const handleEdit = () => {
  window.dispatchEvent(new CustomEvent('google-edit-account'))
}

const handleViewTasks = () => {
  window.dispatchEvent(new CustomEvent('google-view-tasks'))
}

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

// 事件处理函数
const handleSelectionChanged = ((e: CustomEvent) => {
  const { count, account } = e.detail || {}
  selectedCount.value = count || 0
  selectedAccount.value = account || null
}) as EventListener

// ========== 生命周期 ==========
onMounted(async () => {
  await userStore.fetchUserProfile()
  await Promise.all([
    refreshBalance(),
    fetchBrowserStatus()
  ])

  // 监听子组件更新选中数量
  window.addEventListener('google-selection-changed', handleSelectionChanged)
})

onUnmounted(() => {
  window.removeEventListener('google-selection-changed', handleSelectionChanged)
})
</script>
