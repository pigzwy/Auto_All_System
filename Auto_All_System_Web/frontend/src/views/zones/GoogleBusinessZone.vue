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

        <!-- 统一功能入口 -->
        <div class="flex flex-wrap items-center gap-1.5">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="outline" size="sm" class="gap-2">
                自动化
                <ChevronDown class="h-4 w-4 opacity-70" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" class="w-44">
              <DropdownMenuItem :disabled="selectedCount === 0" @select="openOneClickDialog">
                一键全自动
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem :disabled="loading" @select="refreshAccounts">
                刷新
              </DropdownMenuItem>
              <DropdownMenuItem @select="openAddDialog">添加账号</DropdownMenuItem>
              <DropdownMenuItem @select="openImportDialog">批量导入</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem @select="handleExport('csv')">导出 CSV</DropdownMenuItem>
              <DropdownMenuItem @select="handleExport('txt')">导出 TXT</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem :disabled="selectedCount !== 1" @select="handleLaunchGeekez">
                {{ geekezActionLabel }}
              </DropdownMenuItem>
              <DropdownMenuItem :disabled="selectedCount !== 1" @select="handleEdit">编辑</DropdownMenuItem>
              <DropdownMenuItem :disabled="selectedCount !== 1" @select="handleViewTasks">日志</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-destructive" :disabled="selectedCount === 0" @select="handleBulkDelete">
                批量删除
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem :disabled="selectedCount === 0" @select="handleSecurityCommand('change_2fa')">安全设置：修改 2FA</DropdownMenuItem>
              <DropdownMenuItem :disabled="selectedCount === 0" @select="handleSecurityCommand('change_recovery')">安全设置：修改辅助邮箱</DropdownMenuItem>
              <DropdownMenuItem :disabled="selectedCount === 0" @select="handleSecurityCommand('get_backup_codes')">安全设置：获取备份码</DropdownMenuItem>
              <DropdownMenuItem :disabled="selectedCount === 0" @select="handleSecurityCommand('one_click_update')">安全设置：一键安全更新</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
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
import { ref, onMounted, onUnmounted, provide, computed } from 'vue'
import {
  ChevronDown,
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
const selectedAccount = ref<any>(null)

const geekezActionLabel = computed(() => {
  if (!selectedAccount.value) return '打开环境'
  return selectedAccount.value.geekez_profile_exists ? '打开环境' : '创建环境'
})

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

const handleLaunchGeekez = () => {
  window.dispatchEvent(new CustomEvent('google-launch-geekez'))
}

const handleEdit = () => {
  window.dispatchEvent(new CustomEvent('google-edit-account'))
}

const handleViewTasks = () => {
  window.dispatchEvent(new CustomEvent('google-view-tasks'))
}

const handleSelectionChanged = ((e: CustomEvent) => {
  const { count, account } = e.detail || {}
  selectedCount.value = count || 0
  selectedAccount.value = account || null
}) as EventListener

onMounted(() => {
  window.addEventListener('google-selection-changed', handleSelectionChanged)
})

onUnmounted(() => {
  window.removeEventListener('google-selection-changed', handleSelectionChanged)
})
</script>
