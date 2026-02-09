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

    <Dialog v-model:open="selfRegisterDialogOpen">
      <DialogContent class="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle>自动化开通 - 选卡策略</DialogTitle>
          <DialogDescription>
            可从卡池选定一张有效卡、随机使用有效卡，或跳过选卡改为手动输入。
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4 py-2">
          <div class="rounded-lg border border-border/80 bg-muted/20 p-3 text-sm text-muted-foreground">
            本次将开通 <span class="font-semibold text-foreground">{{ selfRegisterTargetIds.length }}</span> 个母号。
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium text-foreground">选卡方式</label>
            <Select v-model="selfRegisterCardMode">
              <SelectTrigger>
                <SelectValue placeholder="请选择选卡方式" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="selected">指定一张有效卡</SelectItem>
                <SelectItem value="random">随机有效卡</SelectItem>
                <SelectItem value="manual">跳过选卡，手动输入</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div v-if="selfRegisterCardMode === 'selected'" class="space-y-2">
            <label class="text-sm font-medium text-foreground">有效卡</label>
            <Select :model-value="selfRegisterSelectedCardValue" @update:model-value="(v) => onSelfRegisterCardChange(v)">
              <SelectTrigger>
                <SelectValue :placeholder="availableCardsLoading ? '正在加载卡片...' : '请选择一张有效卡'" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="card in availableCards"
                  :key="card.id"
                  :value="String(card.id)"
                >
                  {{ formatCardOption(card) }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p v-if="!availableCardsLoading && !availableCards.length" class="text-xs text-amber-600">
              当前没有可用有效卡，请改用“手动输入”或先到卡管理新增可用卡。
            </p>
          </div>

          <p v-if="selfRegisterCardMode === 'manual'" class="text-xs text-muted-foreground">
            付款页将不自动填卡，流程会等待你手动输入卡信息。
          </p>

          <div class="rounded-lg border border-border/80 bg-muted/10 p-3">
            <label class="flex cursor-pointer items-start gap-3">
              <Checkbox
                :checked="selfRegisterKeepProfileOnFail"
                @update:checked="selfRegisterKeepProfileOnFail = Boolean($event)"
                class="mt-0.5"
              />
              <span class="space-y-1">
                <span class="block text-sm font-medium text-foreground">失败时保留 Geekez 环境（调试）</span>
                <span class="block text-xs text-muted-foreground">开启后失败不会自动关闭环境，方便直接查看卡在哪一步。</span>
              </span>
            </label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" :disabled="selfRegisterSubmitting" @click="selfRegisterDialogOpen = false">取消</Button>
          <Button :disabled="selfRegisterSubmitting" @click="confirmRunSelfRegister">
            {{ selfRegisterSubmitting ? '启动中...' : '确认开通' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'
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
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import ZoneHeader from '@/components/zones/ZoneHeader.vue'
import { cardsApi } from '@/api/cards'
import {
  gptBusinessApi,
  type GptBusinessAccount,
  type SelfRegisterCardMode
} from '@/api/gpt_business'
import type { Card } from '@/types'
import type { AcceptableValue } from 'reka-ui'
import AccountsModule from './gpt-modules/AccountsModule.vue'

// ========== 账号相关状态 ==========
const accountsLoading = ref(false)
const selectedMother = ref<GptBusinessAccount | null>(null)
const selectedMotherIds = ref<string[]>([])

provide('selectedMother', selectedMother)
provide('selectedMotherIds', selectedMotherIds)
provide('accountsLoading', accountsLoading)

const hasSelection = computed(() => selectedMotherIds.value.length > 0)

const selfRegisterDialogOpen = ref(false)
const selfRegisterSubmitting = ref(false)
const availableCardsLoading = ref(false)
const availableCards = ref<Card[]>([])
const selfRegisterTargetIds = ref<string[]>([])
const selfRegisterCardMode = ref<SelfRegisterCardMode>('selected')
const selfRegisterSelectedCardId = ref<number | null>(null)
const selfRegisterKeepProfileOnFail = ref(true)

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

const formatCardOption = (card: Card) => {
  const masked = card.masked_card_number || `#${card.id}`
  const holder = card.card_holder ? ` · ${card.card_holder}` : ''
  const expiry = card.expiry_month && card.expiry_year ? ` · ${String(card.expiry_month).padStart(2, '0')}/${String(card.expiry_year).slice(-2)}` : ''
  return `${masked}${holder}${expiry}`
}

const selfRegisterSelectedCardValue = computed(() => {
  return selfRegisterSelectedCardId.value ? String(selfRegisterSelectedCardId.value) : ''
})

const onSelfRegisterCardChange = (value: AcceptableValue) => {
  const parsed = Number(value ?? '')
  selfRegisterSelectedCardId.value = Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

const loadAvailableCards = async () => {
  availableCardsLoading.value = true
  try {
    const resp = await cardsApi.getAvailableCards({ page_size: 200 })
    const rows = Array.isArray(resp) ? resp : Array.isArray((resp as any)?.results) ? (resp as any).results : []
    availableCards.value = rows
    if (rows.length > 0 && !selfRegisterSelectedCardId.value) {
      selfRegisterSelectedCardId.value = rows[0].id
    }
  } catch (e: any) {
    availableCards.value = []
    selfRegisterSelectedCardId.value = null
    ElMessage.error(e?.response?.data?.detail || e?.message || '加载可用卡失败')
  } finally {
    availableCardsLoading.value = false
  }
}

const openSelfRegisterDialog = async (ids: string[]) => {
  selfRegisterTargetIds.value = [...ids]
  selfRegisterCardMode.value = 'selected'
  selfRegisterSelectedCardId.value = null
  selfRegisterKeepProfileOnFail.value = true
  selfRegisterDialogOpen.value = true
  await loadAvailableCards()
  if (!availableCards.value.length) {
    selfRegisterCardMode.value = 'manual'
  }
}

watch(selfRegisterDialogOpen, (open) => {
  if (open) return
  selfRegisterSubmitting.value = false
})

const confirmRunSelfRegister = async () => {
  const ids = [...selfRegisterTargetIds.value]
  if (!ids.length) return
  if (selfRegisterCardMode.value === 'selected' && !selfRegisterSelectedCardId.value) {
    ElMessage.warning('请选择一张有效卡')
    return
  }

  selfRegisterSubmitting.value = true
  try {
    await gptBusinessApi.batchSelfRegister({
      mother_ids: ids,
      concurrency: 5,
      open_geekez: true,
      card_mode: selfRegisterCardMode.value,
      selected_card_id: selfRegisterCardMode.value === 'selected' ? selfRegisterSelectedCardId.value || undefined : undefined,
      keep_profile_on_fail: selfRegisterKeepProfileOnFail.value
    })
    const modeText = selfRegisterCardMode.value === 'selected'
      ? '指定卡'
      : selfRegisterCardMode.value === 'random'
        ? '随机卡'
        : '手动输入'
    const keepText = selfRegisterKeepProfileOnFail.value ? '失败保留环境' : '失败自动关闭环境'
    ElMessage.success(`已启动 ${ids.length} 个母号的自动开通（${modeText}，${keepText}）`)
    selfRegisterDialogOpen.value = false
    refreshAccounts()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  } finally {
    selfRegisterSubmitting.value = false
  }
}

const runSelfRegister = async () => {
  const ids = getSelectedIds()
  if (!ids.length) return
  await openSelfRegisterDialog(ids)
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
