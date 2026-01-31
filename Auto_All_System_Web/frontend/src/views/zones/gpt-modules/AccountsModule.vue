<template>
  <div class="space-y-4">
    <!-- 简单标题 -->
    <div>
      <h2 class="text-lg font-semibold text-foreground">账号列表</h2>
      <p class="text-sm text-muted-foreground">母号可展开查看子账号；邮箱由域名邮箱系统随机创建（来源：admin/email）</p>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardContent class="p-0">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-10"></TableHead>
                <TableHead class="min-w-[220px]">母号邮箱</TableHead>
                <TableHead class="min-w-[180px]">账号密码</TableHead>
                <TableHead class="min-w-[180px]">邮箱密码</TableHead>
                <TableHead class="w-24">座位</TableHead>
                <TableHead class="min-w-[120px]">备注</TableHead>
                <TableHead class="w-40">创建时间</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="loading && mothers.length === 0">
                <TableCell colspan="7" class="py-10 text-center">
                  <div class="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    加载中...
                  </div>
                </TableCell>
              </TableRow>
              <template v-else v-for="mother in mothers" :key="mother.id">
                <TableRow
                  class="cursor-pointer hover:bg-muted/50"
                  :class="{ 'bg-muted/50': selectedMotherId === mother.id }"
                  @click="onCurrentChange(mother)"
                >
                  <TableCell>
                    <Button variant="ghost" size="xs" class="h-6 w-6 p-0" @click.stop="toggleExpand(mother.id)">
                      <LayoutList class="h-4 w-4 transition-transform" :class="{ 'rotate-90': expandedRows.has(mother.id) }" />
                    </Button>
                  </TableCell>
                  <TableCell class="font-medium">{{ mother.email }}</TableCell>
                  <TableCell>
                    <div class="flex items-center gap-2">
                      <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ mother.account_password || '-' }}</code>
                      <Button v-if="mother.account_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyAccountPassword(mother)">
                        <Copy class="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div class="flex items-center gap-2">
                      <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ mother.email_password || '-' }}</code>
                      <Button v-if="mother.email_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyEmailPassword(mother)">
                        <Copy class="h-3 w-3" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" class="font-mono">
                      {{ mother.seat_used || 0 }}/{{ mother.seat_total || 0 }}
                    </Badge>
                  </TableCell>
                  <TableCell class="text-muted-foreground text-xs truncate max-w-[120px]">{{ mother.note }}</TableCell>
                  <TableCell class="text-muted-foreground text-xs">{{ formatDate(mother.created_at) }}</TableCell>
                </TableRow>

                <!-- Expanded Child Rows -->
                <TableRow v-if="expandedRows.has(mother.id)">
                  <TableCell colspan="8" class="p-0 bg-muted/10">
                    <div class="p-4 pl-12 border-b border-border">
                      <div class="mb-2 text-xs font-semibold text-muted-foreground">子账号列表 ({{ mother.children?.length || 0 }})</div>
                      <div class="rounded-lg border border-border overflow-hidden bg-background">
                        <Table>
                          <TableHeader class="bg-muted/30">
                            <TableRow>
                              <TableHead>邮箱</TableHead>
                              <TableHead>账号密码</TableHead>
                              <TableHead>邮箱密码</TableHead>
                              <TableHead>备注</TableHead>
                              <TableHead>创建时间</TableHead>
                              <TableHead class="text-right">操作</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            <TableRow v-for="child in mother.children || []" :key="child.id">
                              <TableCell>{{ child.email }}</TableCell>
                              <TableCell>
                                <div class="flex items-center gap-2">
                                  <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ child.account_password || '-' }}</code>
                                  <Button v-if="child.account_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyAccountPassword(child)">
                                    <Copy class="h-3 w-3" />
                                  </Button>
                                </div>
                              </TableCell>
                              <TableCell>
                                <div class="flex items-center gap-2">
                                  <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{{ child.email_password || '-' }}</code>
                                  <Button v-if="child.email_password" variant="ghost" size="xs" class="h-6 w-6" @click.stop="copyEmailPassword(child)">
                                    <Copy class="h-3 w-3" />
                                  </Button>
                                </div>
                              </TableCell>
                              <TableCell class="text-muted-foreground text-xs">{{ child.note }}</TableCell>
                              <TableCell class="text-muted-foreground text-xs">{{ formatDate(child.created_at) }}</TableCell>
                              <TableCell class="text-right">
                                <div class="flex items-center justify-end gap-1">
                                  <Button variant="ghost" size="xs" @click.stop="launchGeekez(child.id)">Geekez</Button>
                                  <Button variant="ghost" size="xs" @click.stop="copyFull(child)">复制</Button>
                                  <Button variant="ghost" size="xs" class="text-destructive hover:text-destructive" @click.stop="removeAccount(child.id)">删除</Button>
                                </div>
                              </TableCell>
                            </TableRow>
                            <TableRow v-if="!mother.children?.length">
                              <TableCell colspan="6" class="text-center text-xs text-muted-foreground py-4">无子账号</TableCell>
                            </TableRow>
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              </template>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>

    <!-- Dialogs follow (will be replaced in next step) -->
    <Dialog v-model:open="motherDialogVisible">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>生成母号</DialogTitle>
          <DialogDescription>配置邮箱与座位数生成新的母账号</DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">邮箱配置</label>
            <Select :model-value="String(motherForm.cloudmail_config_id || '')" @update:modelValue="(v) => motherForm.cloudmail_config_id = Number(v)">
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
          <div class="grid gap-2">
            <label class="text-sm font-medium">域名</label>
            <Select v-model="motherForm.domain">
              <SelectTrigger>
                <SelectValue placeholder="留空=随机" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">随机</SelectItem>
                <SelectItem v-for="d in motherDomains" :key="d" :value="d">{{ d }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="grid gap-2">
              <label class="text-sm font-medium">座位数</label>
              <Input :model-value="motherForm.seat_total" @update:modelValue="(v) => motherForm.seat_total = Number(v)" type="number" :min="0" :max="500" />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">生成数量</label>
              <Input :model-value="motherForm.count" @update:modelValue="(v) => motherForm.count = Number(v)" type="number" :min="1" :max="200" />
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <textarea
              v-model="motherForm.note"
              rows="2"
              class="min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="可选"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="motherDialogVisible = false">取消</Button>
          <Button :disabled="creating" @click="createMother">
            <Loader2 v-if="creating" class="mr-2 h-4 w-4 animate-spin" />
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="childDialogVisible">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>生成子账号</DialogTitle>
          <DialogDescription>为 {{ selectedMother?.email }} 生成子号</DialogDescription>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">域名</label>
            <Select v-model="childForm.domain">
              <SelectTrigger>
                <SelectValue placeholder="留空=随机" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">随机</SelectItem>
                <SelectItem v-for="d in childDomains" :key="d" :value="d">{{ d }}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">生成数量</label>
            <Input :model-value="childForm.count" @update:modelValue="(v) => childForm.count = Number(v)" type="number" :min="1" :max="500" />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">备注</label>
            <textarea
              v-model="childForm.note"
              rows="2"
              class="min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="可选"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="childDialogVisible = false">取消</Button>
          <Button :disabled="creating" @click="createChild">
            <Loader2 v-if="creating" class="mr-2 h-4 w-4 animate-spin" />
            创建
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Tasks Sheet -->
    <Sheet v-model:open="tasksDrawerVisible">
      <SheetContent side="right" class="w-full sm:max-w-[800px]">
        <SheetHeader>
          <SheetTitle>任务日志</SheetTitle>
          <SheetDescription>账号：{{ tasksDrawerAccount?.email }}</SheetDescription>
        </SheetHeader>
        <div class="mt-4 h-[calc(100vh-140px)] overflow-y-auto">
          <div v-if="tasksLoading" class="py-10 text-center text-muted-foreground">
            <Loader2 class="mx-auto h-6 w-6 animate-spin" />
            <span class="mt-2 block text-sm">加载中...</span>
          </div>
          <div v-else>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>时间</TableHead>
                  <TableHead>错误</TableHead>
                  <TableHead class="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="task in accountTasks" :key="task.id">
                  <TableCell>
                    <Badge variant="outline">{{ getTaskTypeName(task.type || '') }}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge :variant="getStatusTag(task.status || '') === 'success' ? 'default' : 'destructive'">
                      {{ task.status }}
                    </Badge>
                  </TableCell>
                  <TableCell class="text-xs text-muted-foreground">{{ formatDate(task.created_at) }}</TableCell>
                  <TableCell class="text-xs text-destructive max-w-[150px] truncate" :title="task.error">{{ task.error || '-' }}</TableCell>
                  <TableCell class="text-right">
                    <div class="flex justify-end gap-2">
                      <Button variant="ghost" size="xs" @click="viewTaskArtifacts(task)">产物</Button>
                      <Button variant="ghost" size="xs" @click="viewTaskLog(task)">日志</Button>
                    </div>
                  </TableCell>
                </TableRow>
                <TableRow v-if="accountTasks.length === 0">
                  <TableCell colspan="5" class="py-8 text-center text-sm text-muted-foreground">暂无记录</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>
      </SheetContent>
    </Sheet>

    <!-- Artifacts Dialog -->
    <Dialog v-model:open="artifactsDialogVisible">
      <DialogContent class="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>任务产物</DialogTitle>
        </DialogHeader>
        <div class="py-2">
          <div v-if="artifactsLoading" class="py-4 text-center">
            <Loader2 class="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
          </div>
          <Table v-else>
            <TableHeader>
              <TableRow>
                <TableHead>文件</TableHead>
                <TableHead class="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="art in currentTaskArtifacts" :key="art.name">
                <TableCell class="font-mono text-xs">{{ art.name }}</TableCell>
                <TableCell class="text-right">
                  <a :href="art.download_url" target="_blank" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-primary underline-offset-4 hover:underline h-9 px-3">
                    <FileDown class="mr-2 h-4 w-4" /> 下载
                  </a>
                </TableCell>
              </TableRow>
              <TableRow v-if="currentTaskArtifacts.length === 0">
                <TableCell colspan="2" class="py-4 text-center text-sm text-muted-foreground">无产物</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </DialogContent>
    </Dialog>

    <!-- Log Dialog -->
    <Dialog v-model:open="taskLogDialogVisible">
      <DialogContent class="sm:max-w-[900px]">
        <DialogHeader>
          <DialogTitle>任务日志</DialogTitle>
          <DialogDescription v-if="currentLogTask">Task ID: {{ currentLogTask.id }}</DialogDescription>
        </DialogHeader>
        <div class="py-2">
          <div class="mb-2 flex items-center justify-between">
            <span class="text-xs text-muted-foreground">{{ currentLogFilename }}</span>
            <div class="flex gap-2">
              <a v-if="currentLogDownloadUrl" :href="currentLogDownloadUrl" target="_blank" class="text-xs text-primary hover:underline">下载日志</a>
              <button class="text-xs text-primary hover:underline" @click="reloadTaskLog">刷新</button>
            </div>
          </div>
          <textarea
            v-if="!taskLogLoading"
            class="h-[400px] w-full rounded-md border border-input bg-muted/50 p-4 font-mono text-xs text-foreground focus-visible:outline-none"
            readonly
            :value="taskLogText || '暂无日志内容'"
          ></textarea>
          <div v-else class="flex h-[400px] items-center justify-center">
            <Loader2 class="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, reactive, ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import {
  Copy,
  Loader2,
  LayoutList,
  FileDown
} from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

import { getCloudMailConfigs, type CloudMailConfig } from '@/api/email'
import type { GptBusinessAccount, GptBusinessAccountsResponse } from '@/api/gpt_business'
import { gptBusinessApi } from '@/api/gpt_business'

type MotherRow = GptBusinessAccountsResponse['mothers'][number]

// 从父组件注入状态
const selectedMother = inject<Ref<GptBusinessAccount | null>>('selectedMother')!
const accountsLoading = inject<Ref<boolean>>('accountsLoading')!

const loading = ref(false)
const creating = ref(false)
const cloudMailConfigs = ref<CloudMailConfig[]>([])

const mothers = ref<any[]>([])
const selectedMotherId = computed(() => selectedMother.value?.id)

const formatDate = (date: string | undefined) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

const expandedRows = ref(new Set<number>())
const toggleExpand = (id: number) => {
  if (expandedRows.value.has(id)) {
    expandedRows.value.delete(id)
  } else {
    expandedRows.value.add(id)
  }
}

const motherDialogVisible = ref(false)
const childDialogVisible = ref(false)

const activeMother = ref<MotherRow | null>(null)

const motherForm = reactive({
  cloudmail_config_id: 0,
  domain: '',
  seat_total: 4,
  count: 1,
  note: ''
})

const childForm = reactive({
  domain: '',
  count: 1,
  note: ''
})

const selectedMotherConfig = computed(() => {
  if (!motherForm.cloudmail_config_id) return null
  return cloudMailConfigs.value.find(c => c.id === motherForm.cloudmail_config_id) || null
})

const motherDomains = computed(() => {
  return selectedMotherConfig.value?.domains || []
})

const childDomains = computed(() => {
  const configId = activeMother.value?.cloudmail_config_id
  if (!configId) return []
  const cfg = cloudMailConfigs.value.find(c => c.id === configId)
  return cfg?.domains || []
})

const fetchCloudMailConfigs = async () => {
  const res = await getCloudMailConfigs()
  const list = Array.isArray(res) ? res : res.results || []
  cloudMailConfigs.value = list.filter(c => c.is_active)
}

const refresh = async () => {
  loading.value = true
  accountsLoading.value = true
  try {
    const [accounts, _configs] = await Promise.all([gptBusinessApi.listAccounts(), fetchCloudMailConfigs()])
    mothers.value = accounts.mothers || []

    // 重新对齐当前选中
    const currentId = selectedMother.value?.id
    if (currentId) {
      const exists = mothers.value.find((m: any) => m.id === currentId)
      if (!exists) {
        selectedMother.value = null
      } else {
        selectedMother.value = exists
      }
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
    accountsLoading.value = false
  }
}

const onCurrentChange = (row: any) => {
  selectedMother.value = row || null
  activeMother.value = row || null
}

const openCreateMother = () => {
  const defaultCfg = cloudMailConfigs.value.find(c => c.is_default) || cloudMailConfigs.value[0]
  motherForm.cloudmail_config_id = defaultCfg?.id || 0
  motherForm.domain = ''
  motherForm.seat_total = 4
  motherForm.count = 1
  motherForm.note = ''
  motherDialogVisible.value = true
}

const createMother = async () => {
  if (!motherForm.cloudmail_config_id) {
    ElMessage.warning('请先选择邮箱配置')
    return
  }
  creating.value = true
  try {
    const res = await gptBusinessApi.createMotherAccounts({
      cloudmail_config_id: motherForm.cloudmail_config_id,
      domain: motherForm.domain || undefined,
      seat_total: motherForm.seat_total,
      count: motherForm.count,
      note: motherForm.note || undefined
    })
    ElMessage.success(`已创建母号 x${res.created?.length || 0}`)
    motherDialogVisible.value = false
    await refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const openCreateChild = (mother: MotherRow) => {
  activeMother.value = mother
  childForm.domain = ''
  childForm.count = 1
  childForm.note = ''
  childDialogVisible.value = true
}

const createChild = async () => {
  if (!activeMother.value) return
  creating.value = true
  try {
    const res = await gptBusinessApi.createChildAccounts({
      parent_id: activeMother.value.id,
      cloudmail_config_id: activeMother.value.cloudmail_config_id || undefined,
      domain: childForm.domain || undefined,
      count: childForm.count,
      note: childForm.note || undefined
    })
    ElMessage.success(`已创建子号 x${res.created?.length || 0}`)
    childDialogVisible.value = false
    await refresh()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const copyText = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败（浏览器不支持剪贴板）')
  }
}

const copyFull = (acc: GptBusinessAccount) => {
  const lines = [
    acc.email,
    acc.account_password ? `account_password: ${acc.account_password}` : '',
    acc.email_password ? `email_password: ${acc.email_password}` : ''
  ].filter(Boolean)
  copyText(lines.join('\n'))
}

const copyAccountPassword = (acc: GptBusinessAccount) => {
  if (!acc.account_password) return
  copyText(acc.account_password)
}

const copyEmailPassword = (acc: GptBusinessAccount) => {
  if (!acc.email_password) return
  copyText(acc.email_password)
}


const removeAccount = async (accountId: string) => {
  try {
    await ElMessageBox.confirm('删除后不可恢复；删除母号会同时删除其子账号。确认删除？', '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await gptBusinessApi.deleteAccount(accountId)
    ElMessage.success('已删除')
    await refresh()
  } catch (e: any) {
    if (e === 'cancel' || e?.message === 'cancel') return
    ElMessage.error(e?.response?.data?.detail || e?.message || '删除失败')
  }
}

const launchGeekez = async (accountId: string) => {
  try {
    const res = await gptBusinessApi.launchGeekez(accountId)
    if (res?.success) {
      ElMessage.success('已启动 Geekez 环境')
    } else {
      ElMessage.warning('启动失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '启动失败')
  }
}




const tasksDrawerVisible = ref(false)
const tasksDrawerAccount = ref<MotherRow | null>(null)
type TaskRow = {
  id: string
  type?: string
  status?: string
  mother_id?: string
  created_at?: string
  error?: string
}

type TaskArtifact = { name: string; download_url: string }

const accountTasks = ref<TaskRow[]>([])
const tasksLoading = ref(false)

const artifactsDialogVisible = ref(false)
const artifactsLoading = ref(false)
const currentTaskArtifacts = ref<TaskArtifact[]>([])

const taskLogDialogVisible = ref(false)
const taskLogLoading = ref(false)
const currentLogTask = ref<TaskRow | null>(null)
const currentLogFilename = ref('run.log')
const currentLogDownloadUrl = ref('')
const taskLogText = ref('')

const viewTasks = async (mother: MotherRow) => {
  tasksDrawerAccount.value = mother
  tasksDrawerVisible.value = true
  tasksLoading.value = true
  try {
    const res = await gptBusinessApi.getAccountTasks(mother.id)
    const allTasks: TaskRow[] = (res?.tasks || []) as TaskRow[]
    accountTasks.value = allTasks
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取任务失败')
    accountTasks.value = []
  } finally {
    tasksLoading.value = false
  }
}

const viewTaskArtifacts = async (task: TaskRow) => {
  if (!task?.id) return
  artifactsDialogVisible.value = true
  artifactsLoading.value = true
  currentTaskArtifacts.value = []
  try {
    const artifacts = await gptBusinessApi.getTaskArtifacts(task.id)
    currentTaskArtifacts.value = artifacts || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取产物失败')
    currentTaskArtifacts.value = []
  } finally {
    artifactsLoading.value = false
  }
}

const loadTaskLog = async (task: TaskRow) => {
  if (!task?.id) return
  taskLogLoading.value = true
  currentLogTask.value = task
  taskLogText.value = ''
  currentLogFilename.value = 'run.log'
  currentLogDownloadUrl.value = ''
  try {
    const res = await gptBusinessApi.getTaskLog(task.id, { tail: 2000 })
    currentLogFilename.value = res?.filename || 'run.log'
    currentLogDownloadUrl.value = res?.download_url || ''
    taskLogText.value = res?.text || ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || e?.message || '获取日志失败')
    taskLogText.value = ''
    currentLogDownloadUrl.value = ''
  } finally {
    taskLogLoading.value = false
  }
}

const viewTaskLog = async (task: TaskRow) => {
  if (!task?.id) return
  taskLogDialogVisible.value = true
  await loadTaskLog(task)
}

const reloadTaskLog = async () => {
  if (!currentLogTask.value) return
  await loadTaskLog(currentLogTask.value)
}

const getTaskTypeName = (type: string) => {
  const map: Record<string, string> = {
    self_register: '自动开通',
    auto_invite: '自动邀请',
    sub2api_sink: '自动入池'
  }
  return map[type] || type
}

const getStatusTag = (status: string) => {
  const map: Record<string, string> = {
    success: 'success',
    failed: 'danger',
    running: 'primary',
    pending: 'info'
  }
  return map[status] || 'info'
}

// 事件处理函数
const handleRefresh = () => refresh()
const handleOpenCreateMother = () => openCreateMother()
const handleOpenCreateChild = (e: Event) => {
  const mother = (e as CustomEvent).detail
  if (mother) openCreateChild(mother)
}
const handleViewTasks = (e: Event) => {
  const mother = (e as CustomEvent).detail
  if (mother) viewTasks(mother)
}

onMounted(() => {
  refresh()
  
  // 监听父组件发出的事件
  window.addEventListener('gpt-accounts-refresh', handleRefresh)
  window.addEventListener('gpt-open-create-mother', handleOpenCreateMother)
  window.addEventListener('gpt-open-create-child', handleOpenCreateChild)
  window.addEventListener('gpt-view-tasks', handleViewTasks)
})

onUnmounted(() => {
  // 清理事件监听
  window.removeEventListener('gpt-accounts-refresh', handleRefresh)
  window.removeEventListener('gpt-open-create-mother', handleOpenCreateMother)
  window.removeEventListener('gpt-open-create-child', handleOpenCreateChild)
  window.removeEventListener('gpt-view-tasks', handleViewTasks)
})
</script>
