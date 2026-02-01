<template>
  <div class="min-h-screen bg-gradient-to-b from-background to-muted/30 text-foreground">
    <!-- 顶部导航栏 -->
    <header class="sticky top-0 z-30 border-b border-border/50 bg-background/80 backdrop-blur-xl">
      <div class="mx-auto max-w-[1600px] px-6">
        <!-- 主导航行 -->
        <div class="flex h-14 items-center justify-between gap-4">
          <!-- 左侧：返回 + 标题 -->
          <div class="flex items-center gap-4">
            <Button variant="ghost" size="sm" class="gap-2 text-muted-foreground hover:text-foreground" @click="goZones">
              <ChevronLeft class="h-4 w-4" />
              <span class="hidden sm:inline">返回专区</span>
            </Button>
            <div class="h-6 w-px bg-border" />
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                <Sparkles class="h-4 w-4 text-primary" />
              </div>
              <div>
                <h1 class="text-base font-semibold">GPT 业务专区</h1>
              </div>
            </div>
            <Badge variant="outline" class="border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400">Beta</Badge>
          </div>

          <!-- 右侧：用户菜单 -->
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
              <DropdownMenuItem @select="goProfile">
                <UserRound class="mr-2 h-4 w-4" />
                个人资料
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-destructive" @select="logout">
                <LogOut class="mr-2 h-4 w-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <!-- 功能操作栏 -->
        <div class="flex items-center gap-6 border-t border-border/30 py-3">
          <!-- 基础操作 -->
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" class="gap-2" :disabled="accountsLoading" @click="refreshAccounts">
              <RefreshCcw class="h-4 w-4" :class="{ 'animate-spin': accountsLoading }" />
              刷新
            </Button>
            <Button size="sm" class="gap-2" @click="openCreateMother">
              <Plus class="h-4 w-4" />
              生成母号
            </Button>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 已选母号 -->
          <div class="flex items-center gap-3">
            <span class="text-sm text-muted-foreground">当前选择：</span>
            <div v-if="selectedMother" class="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-1.5">
              <div class="h-2 w-2 rounded-full bg-primary animate-pulse" />
              <span class="font-mono text-sm font-medium text-primary">{{ selectedMother.email }}</span>
              <button class="ml-1 rounded p-0.5 hover:bg-primary/20" @click="clearSelection">
                <X class="h-3.5 w-3.5 text-primary/70 hover:text-primary" />
              </button>
            </div>
            <span v-else class="text-sm italic text-muted-foreground/60">点击表格行选择母号</span>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 自动化操作组 -->
          <div class="flex items-center gap-1.5">
            <span class="mr-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">自动化</span>
            <Button size="sm" class="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white" :disabled="!selectedMother" @click="runSelfRegister">
              <UserPlus class="h-4 w-4" />
              开通
            </Button>
            <Button size="sm" class="gap-2 bg-blue-600 hover:bg-blue-700 text-white" :disabled="!selectedMother" @click="runAutoInvite">
              <ArrowRightToLine class="h-4 w-4" />
              邀请
            </Button>
            <Button size="sm" class="gap-2 bg-violet-600 hover:bg-violet-700 text-white" :disabled="!selectedMother" @click="runSub2apiSink">
              <LayoutList class="h-4 w-4" />
              入池
            </Button>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 账号管理组 -->
          <div class="flex items-center gap-1.5">
            <span class="mr-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">管理</span>
            <Button variant="outline" size="sm" class="gap-2 border-orange-500/50 text-orange-600 hover:bg-orange-50 hover:text-orange-700 dark:text-orange-400 dark:hover:bg-orange-950" :disabled="!selectedMother" @click="openCreateChild">
              <Plus class="h-4 w-4" />
              子号
            </Button>
            <Button variant="outline" size="sm" class="gap-2 border-sky-500/50 text-sky-600 hover:bg-sky-50 hover:text-sky-700 dark:text-sky-400 dark:hover:bg-sky-950" :disabled="!selectedMother" @click="editSeat">
              <Settings class="h-4 w-4" />
              座位
            </Button>
            <Button variant="outline" size="sm" class="gap-2 border-slate-500/50 text-slate-600 hover:bg-slate-50 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-900" :disabled="!selectedMother" @click="viewTasks">
              <FileText class="h-4 w-4" />
              日志
            </Button>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 其他操作 -->
          <div class="flex items-center gap-1.5">
            <Button variant="outline" size="sm" class="gap-2 border-teal-500/50 text-teal-600 hover:bg-teal-50 hover:text-teal-700 dark:text-teal-400 dark:hover:bg-teal-950" :disabled="!selectedMother" @click="launchGeekez">
              <ExternalLink class="h-4 w-4" />
              {{ geekezActionLabel }}
            </Button>
            <Button variant="outline" size="sm" class="gap-2 border-red-500/50 text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-950" :disabled="!selectedMother" @click="removeAccount">
              <Trash2 class="h-4 w-4" />
              删除
            </Button>
          </div>
        </div>
      </div>
    </header>

    <!-- 主内容区：直接铺开 -->
    <main class="mx-auto max-w-[1600px] p-6">
      <AccountsModule />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from '@/lib/element'
import {
  ArrowRightToLine,
  ChevronDown,
  ChevronLeft,
  ExternalLink,
  FileText,
  LayoutList,
  LogOut,
  Plus,
  RefreshCcw,
  Settings,
  Sparkles,
  Trash2,
  UserPlus,
  UserRound,
  X
} from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import { gptBusinessApi, type GptBusinessAccount } from '@/api/gpt_business'
import AccountsModule from './gpt-modules/AccountsModule.vue'

const router = useRouter()
const userStore = useUserStore()

// ========== 账号相关状态 ==========
const accountsLoading = ref(false)
const selectedMother = ref<GptBusinessAccount | null>(null)

// 提供给子组件使用
provide('selectedMother', selectedMother)
provide('accountsLoading', accountsLoading)

const clearSelection = () => {
  selectedMother.value = null
}

// 根据环境状态显示按钮文字
const geekezActionLabel = computed(() => {
  if (!selectedMother.value) return '打开环境'
  return selectedMother.value.geekez_profile_exists ? '打开环境' : '创建环境'
})

// ========== 账号操作（委托给 AccountsModule） ==========
const refreshAccounts = () => {
  window.dispatchEvent(new CustomEvent('gpt-accounts-refresh'))
}

const openCreateMother = () => {
  window.dispatchEvent(new CustomEvent('gpt-open-create-mother'))
}

const openCreateChild = () => {
  if (!selectedMother.value) return
  window.dispatchEvent(new CustomEvent('gpt-open-create-child', { detail: selectedMother.value }))
}

const runSelfRegister = async () => {
  if (!selectedMother.value) return
  try {
    const res = await gptBusinessApi.selfRegister(selectedMother.value.id)
    ElMessage.success(res?.message || '已启动：自动开通')
    refreshAccounts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const runAutoInvite = async () => {
  if (!selectedMother.value) return
  try {
    const res = await gptBusinessApi.autoInvite(selectedMother.value.id)
    ElMessage.success(res?.message || '已启动：自动邀请')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const runSub2apiSink = async () => {
  if (!selectedMother.value) return
  try {
    const res = await gptBusinessApi.sub2apiSink(selectedMother.value.id)
    ElMessage.success(res?.message || '已启动：自动入池')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const editSeat = async () => {
  if (!selectedMother.value) return
  try {
    const { value } = await ElMessageBox.prompt('请输入母号座位数（seat_total）', '修改座位', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: String(selectedMother.value.seat_total || 0),
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入非负整数'
    })
    await gptBusinessApi.updateAccount(selectedMother.value.id, { seat_total: Number(value) })
    ElMessage.success('已更新')
    refreshAccounts()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '更新失败')
  }
}

const viewTasks = () => {
  if (!selectedMother.value) return
  window.dispatchEvent(new CustomEvent('gpt-view-tasks', { detail: selectedMother.value }))
}

const launchGeekez = async () => {
  if (!selectedMother.value) return
  try {
    const res = await gptBusinessApi.launchGeekez(selectedMother.value.id)
    if (res?.success) {
      const msg = res.created_profile ? '环境创建并打开成功' : '环境打开成功'
      ElMessage.success(msg)
      // 刷新列表以更新环境状态
      refreshAccounts()
    } else {
      ElMessage.warning('启动失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const removeAccount = async () => {
  if (!selectedMother.value) return
  try {
    await ElMessageBox.confirm('删除后不可恢复；删除母号会同时删除其子账号。确认删除？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await gptBusinessApi.deleteAccount(selectedMother.value.id)
    ElMessage.success('已删除')
    selectedMother.value = null
    refreshAccounts()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

// ========== 导航 ==========
const goZones = () => {
  router.push('/zones')
}

const goProfile = () => {
  router.push('/profile')
}

const logout = async () => {
  await userStore.logout()
  router.replace('/login')
}
</script>
