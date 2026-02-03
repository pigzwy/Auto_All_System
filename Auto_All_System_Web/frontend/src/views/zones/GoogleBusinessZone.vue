<template>
  <div class="min-h-screen bg-gradient-to-b from-background to-muted/30 text-foreground">
    <ZoneHeader>
      <template #toolbar>
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

        <!-- 功能操作栏 -->
        <div class="flex flex-wrap items-center gap-4">
          <!-- 基础操作 -->
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" class="gap-2" :disabled="loading" @click="refreshAccounts">
              <RefreshCcw class="h-4 w-4" :class="{ 'animate-spin': loading }" />
              刷新
            </Button>
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 自动化操作组 -->
          <div class="flex items-center gap-1.5">
            <span class="mr-2 text-xs font-medium text-muted-foreground">自动化</span>
            <Button size="sm" class="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white" :disabled="selectedCount === 0" @click="openOneClickDialog">
              <Wand2 class="h-4 w-4" />
              一键全自动
            </Button>

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
          </div>

          <!-- 分隔线 -->
          <div class="h-8 w-px bg-border/50" />

          <!-- 批量操作 -->
          <div class="flex items-center gap-2">
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
            <Button variant="outline" size="sm" class="gap-2 border-red-500/50 text-red-600 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:hover:bg-red-950" :disabled="selectedCount === 0" @click="handleBulkDelete">
              <Trash2 class="h-4 w-4" />
              批量删除
            </Button>
          </div>
        </div>
      </template>
    </ZoneHeader>

    <!-- 主内容区 -->
    <main class="mx-auto max-w-[1600px] p-6">
      <GoogleAccountsModule ref="accountsModuleRef" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, provide } from 'vue'
import {
  ChevronDown,
  Download,
  Plus,
  RefreshCcw,
  Shield,
  Trash2,
  Upload,
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
import ZoneHeader from '@/components/zones/ZoneHeader.vue'
import GoogleAccountsModule from './google-modules/GoogleAccountsModule.vue'

const accountsModuleRef = ref<InstanceType<typeof GoogleAccountsModule> | null>(null)

const loading = ref(false)
const selectedCount = ref(0)

provide('loading', loading)
provide('selectedCount', selectedCount)

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

const handleSecurityCommand = (command: string) => {
  window.dispatchEvent(new CustomEvent('google-security-command', { detail: command }))
}

const handleBulkDelete = () => {
  window.dispatchEvent(new CustomEvent('google-bulk-delete'))
}

const handleSelectionChanged = ((e: CustomEvent) => {
  const { count } = e.detail || {}
  selectedCount.value = count || 0
}) as EventListener

onMounted(() => {
  window.addEventListener('google-selection-changed', handleSelectionChanged)
})

onUnmounted(() => {
  window.removeEventListener('google-selection-changed', handleSelectionChanged)
})
</script>
