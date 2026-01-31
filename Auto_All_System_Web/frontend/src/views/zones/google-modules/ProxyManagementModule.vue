<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h2 class="text-2xl font-semibold text-foreground">代理管理</h2>
        <p class="mt-1 text-sm text-muted-foreground">维护可用代理池，用于批量自动化任务。</p>
      </div>

      <div class="flex items-center gap-2">
        <Button variant="success" size="sm" class="gap-2" @click="showAddDialog = true">
          <Plus class="h-4 w-4" />
          新增代理
        </Button>
        <Button variant="secondary" size="sm" class="gap-2" @click="showImportDialog = true">
          <Upload class="h-4 w-4" />
          批量导入
        </Button>
      </div>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardContent class="p-0">
        <div class="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>类型</TableHead>
                <TableHead>地址</TableHead>
                <TableHead>用户名</TableHead>
                <TableHead>国家</TableHead>
                <TableHead>状态</TableHead>
                <TableHead class="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="row in proxies" :key="row.id">
                <TableCell>
                  <span class="font-mono text-xs rounded bg-muted px-2 py-1">{{ row.proxy_type }}</span>
                </TableCell>
                <TableCell class="font-mono">{{ row.host }}:{{ row.port }}</TableCell>
                <TableCell class="text-muted-foreground">{{ row.username || '-' }}</TableCell>
                <TableCell class="text-muted-foreground">{{ row.country || '-' }}</TableCell>
                <TableCell>
                  <Badge :variant="row.status === 'active' ? 'default' : 'destructive'" class="rounded-full">
                    {{ row.status === 'active' ? '可用' : '不可用' }}
                  </Badge>
                </TableCell>
                <TableCell class="text-right">
                  <div class="flex items-center justify-end gap-2">
                    <Button variant="outline" size="sm" @click="testProxy(row)">测试</Button>
                    <Button variant="warning" size="sm" type="button" @click="editProxy(row)">编辑</Button>
                    <Button variant="destructive" size="sm" @click="deleteProxy(row)">删除</Button>
                  </div>
                </TableCell>
              </TableRow>

              <TableRow v-if="!loading && proxies.length === 0">
                <TableCell class="py-10 text-center text-muted-foreground" colspan="6">暂无代理</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <div v-if="loading" class="p-4 text-sm text-muted-foreground">加载中...</div>
      </CardContent>
    </Card>

    <!-- 批量导入对话框 -->
    <Dialog v-model:open="showImportDialog">
      <DialogContent class="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>批量导入代理</DialogTitle>
        </DialogHeader>

        <Alert class="mb-3">
          <AlertTitle>格式提示</AlertTitle>
          <AlertDescription>
            <div class="space-y-1 text-sm">
              <div>每行一个代理，格式：socks5://username:password@host:port</div>
              <div>示例：socks5://user1:pass1@1.2.3.4:1080</div>
            </div>
          </AlertDescription>
        </Alert>

        <textarea
          v-model="importText"
          rows="10"
          class="min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          placeholder="粘贴代理数据"
        />

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showImportDialog = false">取消</Button>
          <Button :disabled="importing" class="gap-2" @click="handleImport">
            <Loader2 v-if="importing" class="h-4 w-4 animate-spin" />
            导入
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 新增/编辑代理对话框 -->
    <Dialog v-model:open="showAddDialog">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{{ editingProxy ? '编辑代理' : '新增代理' }}</DialogTitle>
        </DialogHeader>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium">代理类型</label>
            <Select v-model="proxyForm.proxy_type">
              <SelectTrigger>
                <SelectValue placeholder="选择类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="socks5">SOCKS5</SelectItem>
                <SelectItem value="http">HTTP</SelectItem>
                <SelectItem value="https">HTTPS</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">主机地址</label>
            <Input v-model="proxyForm.host" placeholder="1.2.3.4" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">端口</label>
            <Input
              v-model.number="proxyForm.port"
              type="number"
              min="1"
              max="65535"
              placeholder="1080"
            />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">用户名</label>
            <Input v-model="proxyForm.username" placeholder="可选" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium">密码</label>
            <Input
              v-model="proxyForm.password"
              type="password"
              placeholder="可选"
            />
          </div>
        </div>

        <DialogFooter class="gap-2">
          <Button variant="outline" @click="showAddDialog = false">取消</Button>
          <Button :disabled="saving" class="gap-2" @click="handleSave">
            <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Loader2, Plus, Upload } from 'lucide-vue-next'
import { proxiesApi, type Proxy } from '@/api/proxies'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Dialog,
  DialogContent,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// 响应式数据
const loading = ref(false)
const importing = ref(false)
const saving = ref(false)
const proxies = ref<Proxy[]>([])
const showImportDialog = ref(false)
const showAddDialog = ref(false)
const importText = ref('')
const editingProxy = ref<Proxy | null>(null)

const proxyForm = reactive({
  proxy_type: 'socks5' as 'http' | 'https' | 'socks5',
  host: '',
  port: 1080,
  username: '',
  password: ''
})

// 加载代理列表
const loadProxies = async () => {
  loading.value = true
  try {
    const response = await proxiesApi.getProxies()
    proxies.value = response.results || []
  } catch (error: any) {
    ElMessage.error('获取代理列表失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

// 批量导入
const handleImport = async () => {
  if (!importText.value.trim()) {
    ElMessage.warning('请输入代理数据')
    return
  }

  importing.value = true
  try {
    const response = await proxiesApi.batchImport({
      proxy_text: importText.value
    })
    
    if (response.success && response.data) {
      const { success, failed } = response.data
      ElMessage.success(`导入完成: 成功 ${success} 个，失败 ${failed} 个`)
      showImportDialog.value = false
      importText.value = ''
      await loadProxies()
    } else {
      ElMessage.error('导入失败: ' + (response.message || '未知错误'))
    }
  } catch (error: any) {
    ElMessage.error('导入失败: ' + error.message)
  } finally {
    importing.value = false
  }
}

// 保存代理
const handleSave = async () => {
  if (!proxyForm.host || !proxyForm.port) {
    ElMessage.warning('请填写主机地址和端口')
    return
  }

  saving.value = true
  try {
    if (editingProxy.value) {
      // 更新
      await proxiesApi.updateProxy(editingProxy.value.id, proxyForm)
      ElMessage.success('更新成功')
    } else {
      // 新建
      await proxiesApi.createProxy(proxyForm)
      ElMessage.success('创建成功')
    }
    
    showAddDialog.value = false
    editingProxy.value = null
    await loadProxies()
  } catch (error: any) {
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

// 测试代理
const testProxy = async (row: Proxy) => {
  try {
    const response = await proxiesApi.testProxy(row.id)
    if (response.success && response.data) {
      const { ip, country, city } = response.data
      ElMessage.success(`代理连接正常: ${ip} (${country} ${city})`)
      await loadProxies()
    } else {
      ElMessage.error('代理连接失败: ' + (response.message || '未知错误'))
    }
  } catch (error: any) {
    ElMessage.error('代理连接失败: ' + error.message)
  }
}

// 编辑代理
const editProxy = (row: Proxy) => {
  editingProxy.value = row
  proxyForm.proxy_type = row.proxy_type
  proxyForm.host = row.host
  proxyForm.port = row.port
  proxyForm.username = row.username || ''
  proxyForm.password = ''
  showAddDialog.value = true
}

// 删除代理
const deleteProxy = async (row: Proxy) => {
  try {
    await ElMessageBox.confirm('确定删除此代理吗？', '确认删除', {
      type: 'warning'
    })

    await proxiesApi.deleteProxy(row.id)
    ElMessage.success('删除成功')
    await loadProxies()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + error.message)
    }
  }
}

onMounted(() => {
  loadProxies()
})
</script>
