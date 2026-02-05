<template>
  <div class="min-h-screen bg-gradient-to-b from-background to-muted/30 text-foreground">
    <ZoneHeader>
      <template #toolbar>
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
          <div v-if="selectedMotherIds.length" class="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-3 py-1.5">
            <div class="h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span class="font-mono text-sm font-medium text-primary">已选 {{ selectedMotherIds.length }} 项</span>
            <button class="ml-1 rounded p-0.5 hover:bg-primary/20" @click="clearSelection">
              <X class="h-3.5 w-3.5 text-primary/70 hover:text-primary" />
            </button>
          </div>
          <span v-else class="text-sm italic text-muted-foreground/60">点击表格行或勾选多选</span>
        </div>

        <!-- 分隔线 -->
        <div class="h-8 w-px bg-border/50" />

        <!-- 自动化操作组 -->
        <div class="flex items-center gap-1.5">
          <span class="mr-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">自动化</span>
          <Button size="sm" class="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white" :disabled="!hasSelection" @click="runSelfRegister">
            <UserPlus class="h-4 w-4" />
            开通
          </Button>
          <Button size="sm" class="gap-2 bg-blue-600 hover:bg-blue-700 text-white" :disabled="!hasSelection" @click="runAutoInvite">
            <ArrowRightToLine class="h-4 w-4" />
            邀请
          </Button>
          <Button size="sm" class="gap-2 bg-sky-600 hover:bg-sky-700 text-white" :disabled="!hasSelection" @click="runSub2apiSink">
            <LayoutList class="h-4 w-4" />
            入池
          </Button>
          <Button size="sm" class="gap-2 bg-purple-600 hover:bg-purple-700 text-white" :disabled="!hasSelection" @click="openTeamPush">
            <Send class="h-4 w-4" />
            Team
          </Button>
          <Button size="sm" class="gap-2 bg-red-600 hover:bg-red-700 text-white" :disabled="!hasSelection" @click="runBatchDelete">
            删除
          </Button>
        </div>

      </template>
    </ZoneHeader>

    <!-- 主内容区 -->
    <main class="mx-auto max-w-[1600px] p-6">
      <AccountsModule />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, provide, ref } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import {
  ArrowRightToLine,
  LayoutList,
  Plus,
  RefreshCcw,
  Send,
  UserPlus,
  X
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import ZoneHeader from '@/components/zones/ZoneHeader.vue'
import { gptBusinessApi, type GptBusinessAccount } from '@/api/gpt_business'
import AccountsModule from './gpt-modules/AccountsModule.vue'

// ========== 账号相关状态 ==========
const accountsLoading = ref(false)
const selectedMother = ref<GptBusinessAccount | null>(null)
const selectedMotherIds = ref<string[]>([])

provide('selectedMother', selectedMother)
provide('selectedMotherIds', selectedMotherIds)
provide('accountsLoading', accountsLoading)

const hasSelection = computed(() => selectedMotherIds.value.length > 0)

const clearSelection = () => {
  selectedMother.value = null
  selectedMotherIds.value = []
  window.dispatchEvent(new CustomEvent('gpt-selection-clear'))
}

// ========== 账号操作 ==========
const refreshAccounts = () => {
  window.dispatchEvent(new CustomEvent('gpt-accounts-refresh'))
}

const openCreateMother = () => {
  window.dispatchEvent(new CustomEvent('gpt-open-create-mother'))
}

const getSelectedIds = () => {
  if (selectedMotherIds.value.length) return [...selectedMotherIds.value]
  if (selectedMother.value) return [selectedMother.value.id]
  return []
}

const runSelfRegister = async () => {
  const ids = getSelectedIds()
  if (!ids.length) return
  try {
    await gptBusinessApi.batchSelfRegister({
      mother_ids: ids,
      concurrency: 5,
      open_geekez: true
    })
    ElMessage.success(`已启动 ${ids.length} 个母号的自动开通`)
    refreshAccounts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const runAutoInvite = async () => {
  const ids = getSelectedIds()
  if (!ids.length) return
  try {
    await gptBusinessApi.batchAutoInvite({
      mother_ids: ids,
      concurrency: 5,
      open_geekez: true
    })
    ElMessage.success(`已启动 ${ids.length} 个母号的自动邀请`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}

const runSub2apiSink = async () => {
  const ids = getSelectedIds()
  if (!ids.length) return
  window.dispatchEvent(
    new CustomEvent('gpt-open-sub2api-sink', {
      detail: { mother_ids: ids }
    })
  )
}

const runBatchDelete = async () => {
  const ids = getSelectedIds()
  if (!ids.length) return
  try {
    await ElMessageBox.confirm('删除后不可恢复；删除母号会同时删除其子账号。确认删除？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await Promise.all(ids.map(id => gptBusinessApi.deleteAccount(id)))
    ElMessage.success(`已删除 ${ids.length} 个账号`)
    clearSelection()
    refreshAccounts()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

const openTeamPush = () => {
  const ids = getSelectedIds()
  if (!ids.length) return
  window.dispatchEvent(
    new CustomEvent('gpt-open-team-push', {
      detail: { mother_ids: ids }
    })
  )
}

</script>
