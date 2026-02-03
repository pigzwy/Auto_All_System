<template>
  <div class="space-y-6 p-5">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">代理管理</h1>
        <p class="mt-1 text-sm text-muted-foreground">维护代理池、可用性和延迟情况。</p>
      </div>
      <Button variant="success" type="button" class="gap-2" @click="showDialog = true">
        <Plus class="h-4 w-4" />
        添加代理
      </Button>
    </div>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="p-6">
        <div class="relative overflow-hidden rounded-xl border border-border">
          <div
            v-if="loading"
            class="absolute inset-0 z-10 flex items-center justify-center bg-background/60 backdrop-blur-sm"
          >
            <Loading class="h-8 w-8 animate-spin text-muted-foreground" />
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[60px]">ID</TableHead>
                <TableHead class="w-[100px]">类型</TableHead>
                <TableHead class="w-[150px]">主机</TableHead>
                <TableHead class="w-[80px]">端口</TableHead>
                <TableHead class="w-[120px]">用户名</TableHead>
                <TableHead class="w-[100px]">状态</TableHead>
                <TableHead class="w-[100px]">延迟</TableHead>
                <TableHead class="w-[100px]">使用次数</TableHead>
                <TableHead class="w-[180px]">最后检测</TableHead>
                <TableHead class="w-[250px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="(row, idx) in proxies" :key="row.id ?? idx" :class="idx % 2 === 1 ? 'bg-muted/10' : ''">
                <TableCell class="w-[60px]">{{ row.id }}</TableCell>
                <TableCell class="w-[100px]">
                  <Badge variant="secondary" class="rounded-full">{{ getProxyType(row.proxy_type) }}</Badge>
                </TableCell>
                <TableCell class="w-[150px]">{{ row.host }}</TableCell>
                <TableCell class="w-[80px]">{{ row.port }}</TableCell>
                <TableCell class="w-[120px]">{{ row.username || '-' }}</TableCell>
                <TableCell class="w-[100px]">
                  <Badge variant="outline" class="rounded-full" :class="row.status === 'active' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700' : 'border-rose-500/20 bg-rose-500/10 text-rose-700'">
                    {{ row.status === 'active' ? '可用' : '禁用' }}
                  </Badge>
                </TableCell>
                <TableCell class="w-[100px]">
                  <span :class="getLatencyClass(row.response_time)">
                    {{ row.response_time ? `${row.response_time}ms` : '-' }}
                  </span>
                </TableCell>
                <TableCell class="w-[100px]">{{ row.use_count ?? 0 }}</TableCell>
                <TableCell class="w-[180px]">{{ row.last_check_at || '-' }}</TableCell>
                <TableCell class="w-[250px] text-right">
                  <div class="flex items-center justify-end gap-2">
                    <Button type="button" variant="ghost" size="sm" class="text-warning hover:text-warning" @click="editProxy(row)">编辑</Button>
                    <Button type="button" variant="ghost" size="sm" @click="testProxy(row)">测试</Button>
                    <Button type="button" variant="outline" size="sm" @click="toggleActive(row)">
                      {{ row.status === 'active' ? '禁用' : '启用' }}
                    </Button>
                    <Button type="button" variant="ghost" size="sm" class="text-rose-600" @click="deleteProxy(row)">删除</Button>
                  </div>
                </TableCell>
              </TableRow>

              <TableRow v-if="!proxies.length">
                <TableCell :colspan="10" class="py-10 text-center text-sm text-muted-foreground">暂无数据</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>

    <!-- 添加/编辑对话框 -->
    <Dialog v-model:open="showDialog">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{{ editingProxy ? '编辑代理' : '添加代理' }}</DialogTitle>
        </DialogHeader>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">类型</label>
            <Select v-model="formData.proxy_type">
              <SelectTrigger>
                <SelectValue placeholder="选择类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="http">HTTP</SelectItem>
                <SelectItem value="https">HTTPS</SelectItem>
                <SelectItem value="socks5">SOCKS5</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">主机</label>
            <Input v-model="formData.host" placeholder="IP或域名" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">端口</label>
            <Input v-model.number="formData.port" type="number" min="1" max="65535" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">用户名</label>
            <Input v-model="formData.username" placeholder="可选" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">密码</label>
            <Input v-model="formData.password" type="password" placeholder="可选" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">启用</label>
            <div class="flex items-center gap-3">
              <Switch :checked="isActive" @update:checked="isActive = $event" />
              <span class="text-sm text-muted-foreground">{{ isActive ? '可用' : '禁用' }}</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="secondary" @click="showDialog = false">取消</Button>
          <Button type="button" @click="handleSave">保存</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Plus, Loading } from '@/icons'
import { proxiesApi } from '@/api/proxies'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const proxies = ref<any[]>([])
const showDialog = ref(false)
const editingProxy = ref<any>(null)

const formData = reactive<{
  proxy_type: 'http' | 'https' | 'socks5'
  host: string
  port: number
  username: string
  password: string
  status: 'active' | 'inactive'
}>({
  proxy_type: 'http',
  host: '',
  port: 8080,
  username: '',
  password: '',
  status: 'active'
})

const isActive = computed({
  get: () => formData.status === 'active',
  set: (value: boolean) => {
    formData.status = value ? 'active' : 'inactive'
  }
})

const fetchProxies = async () => {
  loading.value = true
  try {
    const response = await proxiesApi.getProxies()
    proxies.value = response.results || []
  } catch (error) {
    console.error('获取代理列表失败:', error)
    ElMessage.error('获取代理列表失败')
  } finally {
    loading.value = false
  }
}

const getProxyType = (type: string) => {
  return type.toUpperCase()
}

const getLatencyClass = (latency?: number | null) => {
  if (!latency) return 'text-muted-foreground'
  if (latency < 100) return 'text-emerald-600'
  if (latency < 300) return 'text-amber-600'
  return 'text-rose-600'
}

const editProxy = (row: any) => {
  editingProxy.value = row
  Object.assign(formData, {
    proxy_type: row.proxy_type,
    host: row.host,
    port: row.port,
    username: row.username || '',
    password: '',
    status: row.status || 'inactive'
  })
  showDialog.value = true
}

const testProxy = async (row: any) => {
  loading.value = true
  try {
    const result = await proxiesApi.testProxy(row.id)
    ElMessage.success(`代理测试成功，延迟: ${result.response_time || 0}ms`)
    fetchProxies()
  } catch (error) {
    console.error('代理测试失败:', error)
    ElMessage.error('代理测试失败')
  } finally {
    loading.value = false
  }
}

const toggleActive = async (row: any) => {
  try {
    const newStatus = row.status === 'active' ? 'inactive' : 'active'
    await proxiesApi.updateProxy(row.id, { status: newStatus })
    ElMessage.success(`已${newStatus === 'active' ? '启用' : '禁用'}代理`)
    fetchProxies()
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error('操作失败')
  }
}

const deleteProxy = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定删除此代理吗？', '提示', {
      type: 'warning'
    })
    await proxiesApi.deleteProxy(row.id)
    ElMessage.success('删除成功')
    fetchProxies()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleSave = async () => {
  try {
    const payload = {
      proxy_type: formData.proxy_type,
      host: formData.host,
      port: formData.port,
      username: formData.username,
      password: formData.password,
      status: formData.status
    }

    if (editingProxy.value) {
      await proxiesApi.updateProxy(editingProxy.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await proxiesApi.createProxy(payload)
      ElMessage.success('添加成功')
    }
    showDialog.value = false
    fetchProxies()
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

onMounted(() => {
  fetchProxies()
})
</script>
