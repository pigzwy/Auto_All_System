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
          <Button size="sm" class="gap-2 bg-teal-600 hover:bg-teal-700 text-white" @click="openQuickRegisterDialog">
            <UserPlus class="h-4 w-4" />
            注册
          </Button>
          <Button size="sm" class="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white" :disabled="!hasSelection" @click="runSelfRegister">
            <UserPlus class="h-4 w-4" />
            开通
          </Button>
          <Button size="sm" class="gap-2 bg-blue-600 hover:bg-blue-700 text-white" :disabled="!hasSelection" @click="runInviteAndPool">
            <ArrowRightToLine class="h-4 w-4" />
            邀请并入池
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
            <label class="text-sm font-medium text-foreground">注册引擎</label>
            <Select v-model="selfRegisterMode">
              <SelectTrigger>
                <SelectValue placeholder="请选择注册引擎" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="browser">浏览器自动化（原流程）</SelectItem>
                <SelectItem value="protocol">协议注册（无浏览器）</SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">
              {{ selfRegisterMode === 'protocol' ? '协议注册将按 protocol_keygen 脚本流程执行，并持久化 token。' : '浏览器自动化会走 Geek 模式打开页面并执行注册。' }}
            </p>
          </div>

          <p v-if="selfRegisterMode === 'browser'" class="text-xs text-muted-foreground">
            浏览器自动化固定使用 Geek 模式，复用已有环境，启动更快。
          </p>

          <div v-if="selfRegisterMode === 'browser'" class="space-y-2">
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

          <div v-if="selfRegisterMode === 'browser' && selfRegisterCardMode === 'selected'" class="space-y-2">
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

          <p v-if="selfRegisterMode === 'browser' && selfRegisterCardMode === 'manual'" class="text-xs text-muted-foreground">
            付款页将不自动填卡，流程会等待你手动输入卡信息。
          </p>

          <div v-if="selfRegisterMode === 'browser'" class="rounded-lg border border-border/80 bg-muted/10 p-3">
            <label class="flex cursor-pointer items-start gap-3">
              <Checkbox
                :checked="selfRegisterKeepProfileOnFail"
                disabled
                @update:checked="selfRegisterKeepProfileOnFail = Boolean($event)"
                class="mt-0.5"
              />
              <span class="space-y-1">
                <span class="block text-sm font-medium text-foreground">失败时保留 Geekez 环境（调试）</span>
                <span class="block text-xs text-muted-foreground">
                  开启后失败不会自动关闭环境，方便直接查看卡在哪一步。
                </span>
              </span>
            </label>
          </div>

          <div class="rounded-lg border border-border/80 bg-muted/10 p-3 space-y-3">
            <label class="flex cursor-pointer items-start gap-3">
              <Checkbox
                v-model:checked="selfRegisterAutoPoolEnabled"
                class="mt-0.5"
              />
              <span class="space-y-1">
                <span class="block text-sm font-medium text-foreground">注册完成后自动入池（S2A）</span>
                <span class="block text-xs text-muted-foreground">
                  勾选后会在注册成功后立即创建并提交 S2A 入池任务。
                </span>
              </span>
            </label>

            <div v-if="selfRegisterAutoPoolEnabled" class="space-y-3">
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A API</label>
                <Input v-model="selfRegisterS2aApiBase" placeholder="例如：https://s2a.example.com" />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A Admin Key</label>
                <Input v-model="selfRegisterS2aAdminKey" placeholder="请输入 Admin Key" />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A Admin Token</label>
                <Input v-model="selfRegisterS2aAdminToken" type="password" placeholder="请输入 Admin Token" />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A 目标 Key（可选）</label>
                <Input v-model="selfRegisterS2aTargetKey" placeholder="留空则使用默认目标" />
              </div>
            </div>
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

    <Dialog v-model:open="quickRegisterDialogOpen">
      <DialogContent class="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle>批量注册（协议模式）</DialogTitle>
          <DialogDescription>
            输入数量后，系统会使用当前邮箱配置生成母号，并自动执行无浏览器协议注册。
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <label class="text-sm font-medium text-foreground">邮箱配置</label>
            <Select :model-value="String(quickRegisterForm.cloudmail_config_id || '')" @update:model-value="(v) => quickRegisterForm.cloudmail_config_id = Number(v)">
              <SelectTrigger>
                <SelectValue placeholder="请选择 admin/email 配置" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="cfg in cloudMailConfigs" :key="cfg.id" :value="String(cfg.id)">
                  {{ cfg.name }}{{ cfg.is_default ? ' (默认)' : '' }} ({{ cfg.domains_count || cfg.domains?.length || 0 }} domains)
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-medium text-foreground">域名</label>
            <Select
              :model-value="quickRegisterForm.domain || '__random__'"
              @update:model-value="(v) => {
                const s = String(v ?? '__random__')
                quickRegisterForm.domain = s === '__random__' ? '' : s
              }"
            >
              <SelectTrigger>
                <SelectValue placeholder="留空=随机" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__random__">随机</SelectItem>
                <SelectItem v-for="d in quickRegisterDomains" :key="d" :value="d">{{ d }}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-2">
              <label class="text-sm font-medium text-foreground">注册数量</label>
              <Input
                :model-value="quickRegisterForm.count"
                @update:model-value="(v) => quickRegisterForm.count = Number(v)"
                type="number"
                :min="1"
                :max="200"
              />
            </div>
            <div class="space-y-2">
              <label class="text-sm font-medium text-foreground">座位数</label>
              <Input
                :model-value="quickRegisterForm.seat_total"
                @update:model-value="(v) => quickRegisterForm.seat_total = Number(v)"
                type="number"
                :min="0"
                :max="500"
              />
            </div>
          </div>

          <div class="rounded-lg border border-border/80 bg-muted/10 p-3 space-y-3">
            <label class="flex cursor-pointer items-start gap-3">
              <Checkbox
                v-model:checked="quickRegisterAutoPoolEnabled"
                class="mt-0.5"
              />
              <span class="space-y-1">
                <span class="block text-sm font-medium text-foreground">注册完成后自动入池（S2A）</span>
                <span class="block text-xs text-muted-foreground">
                  勾选后会在注册成功后自动推送到 S2A；留空将回退到已保存配置。
                </span>
              </span>
            </label>

            <div v-if="quickRegisterAutoPoolEnabled" class="space-y-3">
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A API（可选）</label>
                <Input
                  :model-value="quickRegisterForm.s2a_api_base"
                  @update:model-value="(v) => quickRegisterForm.s2a_api_base = String(v ?? '')"
                  placeholder="留空使用已保存 S2A API"
                />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A Admin Key（可选）</label>
                <Input
                  :model-value="quickRegisterForm.s2a_admin_key"
                  @update:model-value="(v) => quickRegisterForm.s2a_admin_key = String(v ?? '')"
                  placeholder="留空使用已保存 Admin Key"
                />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A Admin Token（可选）</label>
                <Input
                  :model-value="quickRegisterForm.s2a_admin_token"
                  @update:model-value="(v) => quickRegisterForm.s2a_admin_token = String(v ?? '')"
                  type="password"
                  placeholder="留空使用已保存 Admin Token"
                />
              </div>
              <div class="space-y-2">
                <label class="text-sm font-medium text-foreground">S2A 目标 Key（可选）</label>
                <Input
                  :model-value="quickRegisterForm.target_key"
                  @update:model-value="(v) => quickRegisterForm.target_key = String(v ?? '')"
                  placeholder="留空使用默认目标"
                />
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" :disabled="quickRegisterSubmitting" @click="quickRegisterDialogOpen = false">取消</Button>
          <Button :disabled="quickRegisterSubmitting" @click="confirmQuickRegister">
            {{ quickRegisterSubmitting ? '注册中...' : '确认注册' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog :open="quickRegisterLogDialogOpen" @update:open="onQuickRegisterLogDialogOpenChange">
      <DialogContent class="sm:max-w-[980px] max-h-[90vh] flex flex-col">
        <DialogHeader class="shrink-0">
          <DialogTitle>批量注册日志</DialogTitle>
          <DialogDescription>实时刷新任务状态与日志</DialogDescription>
        </DialogHeader>

        <div class="grid grid-cols-4 gap-2 rounded-lg border border-border/70 bg-muted/20 p-3 text-xs">
          <div class="rounded bg-emerald-500/10 px-2 py-1 text-emerald-700">成功 {{ quickRegisterSummary.success }}</div>
          <div class="rounded bg-rose-500/10 px-2 py-1 text-rose-700">失败 {{ quickRegisterSummary.failed }}</div>
          <div class="rounded bg-blue-500/10 px-2 py-1 text-blue-700">进行中 {{ quickRegisterSummary.running }}</div>
          <div class="rounded bg-muted px-2 py-1 text-muted-foreground">总数 {{ quickRegisterSummary.total }}</div>
        </div>

        <div class="flex items-center justify-between rounded-lg border border-border/70 bg-muted/10 px-3 py-2 text-xs">
          <div class="text-muted-foreground">点击左侧账号可查看对应日志</div>
          <div class="inline-flex items-center gap-2">
            <Button size="sm" variant="outline" :disabled="quickRegisterExporting || !quickRegisterTasks.length" @click="exportQuickRegisterTokens">
              {{ quickRegisterExporting ? '导出中...' : '导出Token' }}
            </Button>
            <label class="inline-flex items-center gap-2">
              <Checkbox :checked="quickRegisterAutoRefresh" @update:checked="quickRegisterAutoRefresh = Boolean($event)" />
              <span class="text-muted-foreground">自动刷新</span>
            </label>
          </div>
        </div>

        <div class="min-h-0 flex-1 grid grid-cols-[280px_1fr] gap-3 overflow-hidden">
          <div class="overflow-auto rounded-lg border border-border/70 bg-muted/10 p-2">
            <button
              v-for="item in quickRegisterTasks"
              :key="item.record_id"
              class="mb-2 w-full rounded border px-2 py-2 text-left text-xs transition-colors"
              :class="quickRegisterActiveRecordId === item.record_id ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/40'"
              @click="selectQuickRegisterTask(item.record_id)"
            >
              <div class="font-mono text-[11px] text-foreground">{{ item.email || item.mother_id }}</div>
              <div class="mt-1 flex items-center gap-2 text-[11px]">
                <span
                  class="inline-flex rounded-full px-2 py-0.5"
                  :class="item.status === 'completed'
                    ? 'bg-emerald-500/10 text-emerald-700'
                    : item.status === 'failed'
                      ? 'bg-rose-500/10 text-rose-700'
                      : 'bg-blue-500/10 text-blue-700'"
                >
                  {{ item.status || 'pending' }}
                </span>
                <span class="text-muted-foreground">{{ item.progress_percent || 0 }}%</span>
              </div>
            </button>
          </div>

          <div class="min-h-0 overflow-auto rounded-lg border border-border/70 bg-muted/10 p-3">
            <div class="mb-2 flex items-center justify-between text-xs text-muted-foreground">
              <span>记录 ID: {{ quickRegisterActiveRecordId || '-' }}</span>
              <Button size="sm" variant="outline" :disabled="quickRegisterLogLoading" @click="loadQuickRegisterTaskLog()">刷新</Button>
            </div>
            <pre class="whitespace-pre-wrap break-words text-xs font-mono leading-5 text-foreground">{{ quickRegisterLogText || '暂无日志' }}</pre>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, provide, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import {
  ArrowRightToLine,
  Plus,
  RefreshCcw,
  Send,
  UserPlus,
  X
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
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
import { getCloudMailConfigs, type CloudMailConfig } from '@/api/email'
import {
  gptBusinessApi,
  type GptBusinessAccount,
  type SelfRegisterCardMode,
  type SelfRegisterMode,
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
const selfRegisterMode = ref<SelfRegisterMode>('browser')
const selfRegisterCardMode = ref<SelfRegisterCardMode>('selected')
const selfRegisterSelectedCardId = ref<number | null>(null)
const selfRegisterKeepProfileOnFail = ref(true)
const selfRegisterAutoPoolEnabled = ref(false)
const selfRegisterS2aApiBase = ref('')
const selfRegisterS2aAdminKey = ref('')
const selfRegisterS2aAdminToken = ref('')
const selfRegisterS2aTargetKey = ref('')

const quickRegisterDialogOpen = ref(false)
const quickRegisterSubmitting = ref(false)
const cloudMailConfigs = ref<CloudMailConfig[]>([])
const quickRegisterAutoPoolEnabled = ref(false)
const quickRegisterForm = ref({
  cloudmail_config_id: 0,
  domain: '',
  seat_total: 4,
  count: 1,
  s2a_api_base: '',
  s2a_admin_key: '',
  s2a_admin_token: '',
  target_key: ''
})

const quickRegisterSelectedConfig = computed(() => {
  if (!quickRegisterForm.value.cloudmail_config_id) return null
  return cloudMailConfigs.value.find(c => c.id === quickRegisterForm.value.cloudmail_config_id) || null
})

const quickRegisterDomains = computed(() => {
  return quickRegisterSelectedConfig.value?.domains || []
})

type QuickRegisterTaskItem = {
  mother_id: string
  record_id: string
  task_id: string
  celery_task_id: string
  email: string
  status: string
  progress_percent: number
  error: string
}

const quickRegisterTasks = ref<QuickRegisterTaskItem[]>([])
const quickRegisterActiveRecordId = ref('')
const quickRegisterLogText = ref('')
const quickRegisterLogLoading = ref(false)
const quickRegisterLogDialogOpen = ref(false)
const quickRegisterAutoRefresh = ref(true)
const quickRegisterExporting = ref(false)
let quickRegisterPollingTimer: number | null = null
let quickRegisterPollingInFlight = false

const quickRegisterSummary = computed(() => {
  let success = 0
  let failed = 0
  let running = 0
  for (const task of quickRegisterTasks.value) {
    const status = String(task.status || '').toLowerCase()
    if (status === 'completed' || status === 'success') {
      success += 1
    } else if (status === 'failed' || status === 'cancelled' || status === 'revoked') {
      failed += 1
    } else {
      running += 1
    }
  }
  return {
    total: quickRegisterTasks.value.length,
    success,
    failed,
    running
  }
})

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

const loadCloudMailConfigs = async () => {
  const res = await getCloudMailConfigs()
  const list = Array.isArray(res) ? res : res.results || []
  cloudMailConfigs.value = list.filter(c => c.is_active)
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
  selfRegisterMode.value = 'browser'
  selfRegisterCardMode.value = 'selected'
  selfRegisterSelectedCardId.value = null
  selfRegisterKeepProfileOnFail.value = true
  selfRegisterAutoPoolEnabled.value = false

  // 预加载已保存的 S2A 配置
  try {
    const settings = await gptBusinessApi.getSettings()
    const s2a = settings?.s2a || {}
    selfRegisterS2aApiBase.value = String(s2a.api_base || '').trim()
    selfRegisterS2aAdminKey.value = String(s2a.admin_key || '').trim()
    selfRegisterS2aAdminToken.value = String(s2a.admin_token || '').trim()
    selfRegisterS2aTargetKey.value = String(s2a.target_key || '').trim()
  } catch {
    selfRegisterS2aApiBase.value = ''
    selfRegisterS2aAdminKey.value = ''
    selfRegisterS2aAdminToken.value = ''
    selfRegisterS2aTargetKey.value = ''
  }

  selfRegisterDialogOpen.value = true
  await loadAvailableCards()
  if (!availableCards.value.length) {
    selfRegisterCardMode.value = 'manual'
  }
}

watch(selfRegisterDialogOpen, (open) => {
  if (open) return
  selfRegisterSubmitting.value = false
  selfRegisterS2aAdminToken.value = ''
})

watch(selfRegisterMode, (mode) => {
  if (mode === 'protocol') {
    selfRegisterKeepProfileOnFail.value = false
  }
})

const confirmRunSelfRegister = async () => {
  const ids = [...selfRegisterTargetIds.value]
  if (!ids.length) {
    ElMessage.warning('请先选择母号')
    return
  }
  if (
    selfRegisterMode.value === 'browser' &&
    selfRegisterCardMode.value === 'selected' &&
    !selfRegisterSelectedCardId.value
  ) {
    ElMessage.warning('请选择一张有效卡')
    return
  }

  // S2A 参数支持留空回退到后端已保存配置

  selfRegisterSubmitting.value = true
  try {
    await gptBusinessApi.batchSelfRegister({
      mother_ids: ids,
      concurrency: 5,
      register_mode: selfRegisterMode.value,
      open_geekez: selfRegisterMode.value === 'browser',
      launch_type: selfRegisterMode.value === 'browser' ? 'geekez' : undefined,
      card_mode: selfRegisterMode.value === 'browser' ? selfRegisterCardMode.value : undefined,
      selected_card_id:
        selfRegisterMode.value === 'browser' && selfRegisterCardMode.value === 'selected'
          ? selfRegisterSelectedCardId.value || undefined
          : undefined,
      keep_profile_on_fail:
        selfRegisterMode.value !== 'browser'
          ? false
          : selfRegisterKeepProfileOnFail.value,
      auto_pool_enabled: selfRegisterAutoPoolEnabled.value,
      s2a_api_base: selfRegisterAutoPoolEnabled.value
        ? selfRegisterS2aApiBase.value.trim() || undefined
        : undefined,
      s2a_admin_key: selfRegisterAutoPoolEnabled.value
        ? selfRegisterS2aAdminKey.value.trim() || undefined
        : undefined,
      s2a_admin_token: selfRegisterAutoPoolEnabled.value
        ? selfRegisterS2aAdminToken.value.trim() || undefined
        : undefined,
      target_key: selfRegisterAutoPoolEnabled.value
        ? selfRegisterS2aTargetKey.value.trim() || undefined
        : undefined,
      pool_mode: selfRegisterAutoPoolEnabled.value ? 's2a_oauth' : 'disabled'
    })
    if (selfRegisterMode.value === 'protocol') {
      ElMessage.success(`已启动 ${ids.length} 个母号的协议注册（无浏览器）`)
      selfRegisterDialogOpen.value = false
      refreshAccounts()
      return
    }
    const launchText = 'Geek 模式'
    const modeText = selfRegisterCardMode.value === 'selected'
      ? '指定卡'
      : selfRegisterCardMode.value === 'random'
        ? '随机卡'
        : '手动输入'
    const keepText = selfRegisterKeepProfileOnFail.value
      ? '失败保留环境'
      : '失败自动关闭环境'
    const poolText = selfRegisterAutoPoolEnabled.value
      ? '注册后自动提交 S2A 入池'
      : '不自动入池'
    ElMessage.success(`已启动 ${ids.length} 个母号的自动开通（${launchText}，${modeText}，${keepText}，${poolText}）`)
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
  if (!ids.length) {
    ElMessage.warning('请先选择母号')
    return
  }
  await openSelfRegisterDialog(ids)
}

const openQuickRegisterDialog = async () => {
  await loadCloudMailConfigs()
  const defaultCfg = cloudMailConfigs.value.find(c => c.is_default) || cloudMailConfigs.value[0]

  // 预加载已保存的 S2A 配置
  let savedApiBase = ''
  let savedAdminKey = ''
  let savedAdminToken = ''
  let savedTargetKey = ''
  try {
    const settings = await gptBusinessApi.getSettings()
    const s2a = settings?.s2a || {}
    savedApiBase = String(s2a.api_base || '').trim()
    savedAdminKey = String(s2a.admin_key || '').trim()
    savedAdminToken = String(s2a.admin_token || '').trim()
    savedTargetKey = String(s2a.target_key || '').trim()
  } catch {
    // 获取设置失败时留空，用户可手动输入
  }

  quickRegisterForm.value = {
    cloudmail_config_id: defaultCfg?.id || 0,
    domain: '',
    seat_total: 4,
    count: 1,
    s2a_api_base: savedApiBase,
    s2a_admin_key: savedAdminKey,
    s2a_admin_token: savedAdminToken,
    target_key: savedTargetKey
  }
  quickRegisterAutoPoolEnabled.value = false
  quickRegisterDialogOpen.value = true
}

const confirmQuickRegister = async () => {
  const count = Number(quickRegisterForm.value.count || 0)
  if (!quickRegisterForm.value.cloudmail_config_id) {
    ElMessage.warning('请先选择邮箱配置')
    return
  }
  if (!Number.isFinite(count) || count <= 0) {
    ElMessage.warning('请输入有效注册数量')
    return
  }

  quickRegisterSubmitting.value = true
  try {
    const created = await gptBusinessApi.createMotherAccounts({
      cloudmail_config_id: Number(quickRegisterForm.value.cloudmail_config_id),
      domain: quickRegisterForm.value.domain || undefined,
      seat_total: Number(quickRegisterForm.value.seat_total || 4),
      count: Number(quickRegisterForm.value.count || 1)
    })
    const ids = (created.created || []).map(x => String(x.id || '')).filter(Boolean)
    if (!ids.length) {
      ElMessage.error('创建母号失败：未返回可注册账号')
      return
    }

    const emailByMotherId = new Map(
      (created.created || [])
        .map(acc => [String(acc.id || ''), String(acc.email || '')] as [string, string])
        .filter(([id]) => Boolean(id))
    )

    const batchRes = await gptBusinessApi.batchSelfRegister({
      mother_ids: ids,
      concurrency: 5,
      register_mode: 'protocol',
      auto_pool_enabled: Boolean(quickRegisterAutoPoolEnabled.value),
      s2a_api_base: quickRegisterAutoPoolEnabled.value
        ? String(quickRegisterForm.value.s2a_api_base || '').trim() || undefined
        : undefined,
      s2a_admin_key: quickRegisterAutoPoolEnabled.value
        ? String(quickRegisterForm.value.s2a_admin_key || '').trim() || undefined
        : undefined,
      s2a_admin_token: quickRegisterAutoPoolEnabled.value
        ? String(quickRegisterForm.value.s2a_admin_token || '').trim() || undefined
        : undefined,
      target_key: quickRegisterAutoPoolEnabled.value
        ? String(quickRegisterForm.value.target_key || '').trim() || undefined
        : undefined,
      pool_mode: quickRegisterAutoPoolEnabled.value ? 's2a_oauth' : 'disabled'
    })

    const rows = Array.isArray(batchRes?.results) ? batchRes.results : []
    quickRegisterTasks.value = rows
      .map((x: any) => {
        const motherId = String(x?.mother_id || '')
        const recordId = String(x?.record_id || '')
        const taskId = String(x?.task_id || '')
        return {
          mother_id: motherId,
          record_id: recordId,
          task_id: taskId,
          celery_task_id: '',
          email: emailByMotherId.get(motherId) || '',
          status: 'pending',
          progress_percent: 0,
          error: ''
        }
      })
      .filter(item => Boolean(item.record_id))

    quickRegisterActiveRecordId.value = quickRegisterTasks.value[0]?.record_id || ''
    quickRegisterLogText.value = ''

    ElMessage.success(`已启动 ${ids.length} 个账号的批量注册`)
    quickRegisterDialogOpen.value = false
    quickRegisterLogDialogOpen.value = true
    refreshAccounts()
    await refreshQuickRegisterTasks()
    await loadQuickRegisterTaskLog()
    if (quickRegisterAutoRefresh.value) {
      startQuickRegisterLogPolling()
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '批量注册失败')
  } finally {
    quickRegisterSubmitting.value = false
  }
}

const isQuickRegisterTerminal = (status: string) => {
  const s = String(status || '').toLowerCase()
  return s === 'completed' || s === 'failed' || s === 'cancelled' || s === 'revoked' || s === 'success'
}

const refreshQuickRegisterTasks = async () => {
  if (!quickRegisterTasks.value.length) return
  const snapshots = await Promise.all(
    quickRegisterTasks.value.map(async item => {
      try {
        const task = await gptBusinessApi.getTask(item.record_id)
        return { recordId: item.record_id, task }
      } catch {
        return { recordId: item.record_id, task: null }
      }
    })
  )

  quickRegisterTasks.value = quickRegisterTasks.value.map(item => {
    const hit = snapshots.find(x => x.recordId === item.record_id)
    const task: any = hit?.task
    if (!task) return item
    return {
      ...item,
      status: String(task.status || item.status || 'pending'),
      progress_percent: Number(task.progress_percent || item.progress_percent || 0),
      celery_task_id: String(task.celery_task_id || item.celery_task_id || ''),
      error: String(task.error || item.error || '')
    }
  })
}

const loadQuickRegisterTaskLog = async (recordId?: string) => {
  const rid = String(recordId || quickRegisterActiveRecordId.value || '')
  if (!rid) return

  quickRegisterLogLoading.value = true
  try {
    const res = await gptBusinessApi.getTaskLog(rid, { tail: 1200 })
    const text = String(res?.text || '').trim()
    if (text) {
      quickRegisterLogText.value = text
      return
    }
    const task = quickRegisterTasks.value.find(t => t.record_id === rid)
    quickRegisterLogText.value = task?.error ? `error: ${task.error}` : '暂无日志'
  } catch (e: any) {
    quickRegisterLogText.value = `读取日志失败: ${e?.response?.data?.detail || e?.message || 'unknown error'}`
  } finally {
    quickRegisterLogLoading.value = false
  }
}

const selectQuickRegisterTask = async (recordId: string) => {
  quickRegisterActiveRecordId.value = String(recordId || '')
  await loadQuickRegisterTaskLog(recordId)
}

const downloadTextFile = (filename: string, content: string, mimeType = 'text/plain;charset=utf-8') => {
  const blob = new Blob([content], { type: mimeType })
  const href = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(href)
}

const exportQuickRegisterTokens = async () => {
  if (!quickRegisterTasks.value.length) {
    ElMessage.warning('暂无可导出的注册任务')
    return
  }

  quickRegisterExporting.value = true
  try {
    const candidates = quickRegisterTasks.value.filter(item => {
      const s = String(item.status || '').toLowerCase()
      return s === 'completed' || s === 'success'
    })
    if (!candidates.length) {
      ElMessage.warning('当前没有成功任务，无法导出 Token')
      return
    }

    const tokenArtifacts: Record<string, any>[] = []
    const accessTokens: string[] = []
    const refreshTokens: string[] = []
    const idTokens: string[] = []

    for (const item of candidates) {
      try {
        const res = await gptBusinessApi.getAccountTokens(item.mother_id)
        const artifact = res?.has_tokens ? res?.token_artifact : null
        if (!artifact || typeof artifact !== 'object') continue
        tokenArtifacts.push(artifact)

        const accessToken = String(artifact.access_token || '').trim()
        const refreshToken = String(artifact.refresh_token || '').trim()
        const idToken = String(artifact.id_token || '').trim()
        if (accessToken) accessTokens.push(accessToken)
        if (refreshToken) refreshTokens.push(refreshToken)
        if (idToken) idTokens.push(idToken)
      } catch {
        continue
      }
    }

    if (!tokenArtifacts.length) {
      ElMessage.warning('未获取到可导出的 Token 数据')
      return
    }

    const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
    downloadTextFile(`gpt-register-tokens-${stamp}.json`, JSON.stringify(tokenArtifacts, null, 2), 'application/json;charset=utf-8')
    if (accessTokens.length) downloadTextFile(`gpt-register-ak-${stamp}.txt`, `${accessTokens.join('\n')}\n`)
    if (refreshTokens.length) downloadTextFile(`gpt-register-rk-${stamp}.txt`, `${refreshTokens.join('\n')}\n`)
    if (idTokens.length) downloadTextFile(`gpt-register-id-${stamp}.txt`, `${idTokens.join('\n')}\n`)
    ElMessage.success(`已导出 ${tokenArtifacts.length} 条 Token`)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '导出 Token 失败')
  } finally {
    quickRegisterExporting.value = false
  }
}

const stopQuickRegisterLogPolling = () => {
  if (quickRegisterPollingTimer !== null) {
    window.clearInterval(quickRegisterPollingTimer)
    quickRegisterPollingTimer = null
  }
  quickRegisterPollingInFlight = false
}

const startQuickRegisterLogPolling = () => {
  stopQuickRegisterLogPolling()
  quickRegisterPollingTimer = window.setInterval(async () => {
    if (!quickRegisterLogDialogOpen.value) return
    if (!quickRegisterAutoRefresh.value) return
    if (quickRegisterPollingInFlight) return
    quickRegisterPollingInFlight = true
    try {
      await refreshQuickRegisterTasks()
      await loadQuickRegisterTaskLog()
      const hasRunning = quickRegisterTasks.value.some(item => !isQuickRegisterTerminal(item.status))
      if (!hasRunning) {
        stopQuickRegisterLogPolling()
      }
    } finally {
      quickRegisterPollingInFlight = false
    }
  }, 1500)
}

const onQuickRegisterLogDialogOpenChange = (open: boolean) => {
  quickRegisterLogDialogOpen.value = open
  if (!open) {
    stopQuickRegisterLogPolling()
    return
  }
  if (quickRegisterAutoRefresh.value) {
    startQuickRegisterLogPolling()
  }
}

watch(quickRegisterAutoRefresh, (enabled) => {
  if (!quickRegisterLogDialogOpen.value) return
  if (enabled) {
    startQuickRegisterLogPolling()
  } else {
    stopQuickRegisterLogPolling()
  }
})

onUnmounted(() => {
  stopQuickRegisterLogPolling()
})

const runInviteAndPool = async () => {
  const ids = getSelectedIds()
  if (!ids.length) return
  window.dispatchEvent(
    new CustomEvent('gpt-open-sub2api-sink', {
      detail: {
        mother_ids: ids,
        action: 'invite_and_pool'
      }
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
