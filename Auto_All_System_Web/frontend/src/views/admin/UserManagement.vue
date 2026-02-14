<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">用户管理</h1>
        <p class="mt-1 text-sm text-muted-foreground">管理用户、权限、状态与余额。</p>
      </div>
      <Button variant="success" type="button" class="gap-2" @click="showCreateDialog = true">
        <Plus class="h-4 w-4" />
        添加用户
      </Button>
    </div>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="space-y-4 p-6">
        <!-- 搜索和筛选 -->
        <div class="flex flex-wrap items-end gap-4">
          <div class="grid gap-2">
            <label class="text-sm text-muted-foreground">搜索</label>
            <div class="relative w-full sm:w-72">
              <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model="searchQuery"
                placeholder="用户名/邮箱"
                class="h-9 pl-9"
                @update:modelValue="fetchUsers"
              />
            </div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm text-muted-foreground">状态</label>
            <Select v-model="isActiveFilter">
              <SelectTrigger class="w-full sm:w-36">
                <SelectValue placeholder="全部" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="active">激活</SelectItem>
                <SelectItem value="inactive">禁用</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid gap-2">
            <label class="text-sm text-muted-foreground">角色</label>
            <Select v-model="roleFilter">
              <SelectTrigger class="w-full sm:w-36">
                <SelectValue placeholder="全部" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部</SelectItem>
                <SelectItem value="admin">管理员</SelectItem>
                <SelectItem value="user">用户</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <!-- 用户表格 -->
        <div class="overflow-hidden rounded-xl border border-border bg-background/70 shadow-sm" v-loading="loading">
          <Table>
            <TableHeader>
              <TableRow class="bg-muted/40">
                <TableHead class="w-[80px]">ID</TableHead>
                <TableHead class="w-[150px]">用户名</TableHead>
                <TableHead class="w-[200px]">邮箱</TableHead>
                <TableHead class="w-[120px]">角色</TableHead>
                <TableHead class="w-[100px]">状态</TableHead>
                <TableHead class="w-[120px]">余额</TableHead>
                <TableHead class="w-[180px]">注册时间</TableHead>
                <TableHead class="w-[250px] text-right">操作</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              <TableRow
                v-for="(row, idx) in users"
                :key="row.id"
                :class="[idx % 2 === 1 ? 'bg-muted/10' : '', 'hover:bg-muted/30']"
              >
                <TableCell class="w-[80px]">{{ row.id }}</TableCell>
                <TableCell class="w-[150px]">{{ row.username }}</TableCell>
                <TableCell class="w-[200px]">{{ row.email }}</TableCell>
                <TableCell class="w-[120px]">
                  <Badge
                    v-if="row.role === 'super_admin'"
                    variant="outline"
                    class="border-rose-500/20 bg-rose-500/10 text-rose-700"
                  >
                    超级管理员
                  </Badge>
                  <Badge
                    v-else-if="row.role === 'admin'"
                    variant="outline"
                    class="border-amber-500/20 bg-amber-500/10 text-amber-800"
                  >
                    管理员
                  </Badge>
                  <Badge v-else variant="secondary" class="rounded-full">
                    普通用户
                  </Badge>
                </TableCell>
                <TableCell class="w-[100px]">
                  <Badge
                    variant="outline"
                    class="rounded-full"
                    :class="row.is_active ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700' : 'border-rose-500/20 bg-rose-500/10 text-rose-700'"
                  >
                    {{ row.is_active ? '激活' : '禁用' }}
                  </Badge>
                </TableCell>
                <TableCell class="w-[120px]">¥{{ row.balance || '0.00' }}</TableCell>
                <TableCell class="w-[180px]">{{ formatDate(row.created_at) }}</TableCell>
                <TableCell class="w-[250px] text-right">
                  <div class="flex items-center justify-end gap-2">
                    <Button type="button" variant="ghost" size="sm" class="gap-1 text-warning hover:text-warning" @click="handleEdit(row)">
                      <Edit class="h-4 w-4" />
                      编辑
                    </Button>
                    <Button type="button" variant="ghost" size="sm" class="gap-1 text-amber-700" @click="handleResetPassword(row)">
                      <Key class="h-4 w-4" />
                      重置密码
                    </Button>
                    <Button type="button" variant="ghost" size="sm" class="gap-1 text-rose-600" @click="handleDelete(row)">
                      <Delete class="h-4 w-4" />
                      删除
                    </Button>
                  </div>
                </TableCell>
              </TableRow>

              <TableRow v-if="!users.length">
                <TableCell :colspan="8" class="py-10 text-center text-sm text-muted-foreground">
                  暂无数据
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <!-- 分页 -->
        <div class="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div class="text-sm text-muted-foreground">共 {{ total }} 条</div>
          <div class="flex items-center gap-2">
            <select
              class="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
              :value="pageSize"
              @change="handlePageSizeChange"
            >
              <option v-for="s in [10, 20, 50, 100]" :key="s" :value="s">{{ s }}/页</option>
            </select>

            <Button type="button" variant="outline" size="sm" :disabled="currentPage <= 1" @click="goPrev">上一页</Button>
            <span class="text-sm text-muted-foreground">{{ currentPage }} / {{ totalPages }}</span>
            <Button type="button" variant="outline" size="sm" :disabled="currentPage >= totalPages" @click="goNext">下一页</Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 创建/编辑用户对话框 -->
    <Dialog v-model:open="showCreateDialog">
      <DialogContent class="sm:max-w-[600px] bg-card/95">
        <DialogHeader>
          <DialogTitle>{{ editingUser ? '编辑用户' : '创建用户' }}</DialogTitle>
        </DialogHeader>

        <div class="grid gap-4 py-2">
          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">用户名</label>
            <Input v-model="userForm.username" placeholder="请输入用户名" autocomplete="username" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">邮箱</label>
            <Input v-model="userForm.email" type="email" placeholder="请输入邮箱" autocomplete="email" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">手机号</label>
            <Input v-model="userForm.phone" placeholder="请输入手机号" autocomplete="tel" />
          </div>

          <div v-if="!editingUser" class="grid gap-2">
            <label class="text-sm font-medium text-foreground">密码</label>
            <Input v-model="userForm.password" type="password" placeholder="请输入密码" autocomplete="new-password" />
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">管理员</label>
            <div class="flex items-center gap-3">
              <Switch :checked="userForm.is_staff" @update:checked="userForm.is_staff = $event" />
              <span class="text-sm text-muted-foreground">{{ userForm.is_staff ? '是' : '否' }}</span>
            </div>
          </div>

          <div class="grid gap-2">
            <label class="text-sm font-medium text-foreground">状态</label>
            <div class="flex items-center gap-3">
              <Switch :checked="userForm.is_active" @update:checked="userForm.is_active = $event" />
              <span class="text-sm text-muted-foreground">{{ userForm.is_active ? '激活' : '禁用' }}</span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="secondary" @click="showCreateDialog = false">取消</Button>
          <Button type="button" class="gap-2" :disabled="saving" @click="handleSaveUser">
            <Loading v-if="saving" class="h-4 w-4 animate-spin" />
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { Plus, Search, Edit, Delete, Key, Loading } from '@/icons'
import dayjs from 'dayjs'
import usersApi, { type User } from '@/api/users'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const saving = ref(false)
const showCreateDialog = ref(false)
const editingUser = ref<User | null>(null)
const searchQuery = ref('')
const users = ref<User[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const filters = reactive({
  is_active: null as boolean | null,
  role: ''
})

const isActiveFilter = computed<string>({
  get: () => {
    if (filters.is_active === null) return 'all'
    return filters.is_active ? 'active' : 'inactive'
  },
  set: (val) => {
    filters.is_active = val === 'all' ? null : val === 'active'
    fetchUsers()
  },
})

const roleFilter = computed<string>({
  get: () => filters.role || 'all',
  set: (val) => {
    filters.role = val === 'all' ? '' : val
    fetchUsers()
  },
})

const userForm = reactive({
  id: 0,
  username: '',
  email: '',
  phone: '',
  password: '',
  is_staff: false,
  is_active: true
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

const handlePageSizeChange = (e: Event) => {
  const val = Number((e.target as HTMLSelectElement).value)
  if (!Number.isFinite(val) || val <= 0) return
  pageSize.value = val
  currentPage.value = 1
  fetchUsers()
}

const goPrev = () => {
  if (currentPage.value <= 1) return
  currentPage.value -= 1
  fetchUsers()
}

const goNext = () => {
  if (currentPage.value >= totalPages.value) return
  currentPage.value += 1
  fetchUsers()
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    
    if (searchQuery.value) {
      params.search = searchQuery.value
    }
    
    if (filters.is_active !== null) {
      params.is_active = filters.is_active
    }
    
    if (filters.role === 'admin') {
      params.is_staff = true
    } else if (filters.role === 'user') {
      params.is_staff = false
    }
    
    const response = await usersApi.getUsers(params)
    users.value = response.results
    total.value = response.count
  } catch (error) {
    console.error('Failed to fetch users:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleEdit = (user: User) => {
  editingUser.value = user
  userForm.id = user.id
  userForm.username = user.username
  userForm.email = user.email
  userForm.phone = user.phone || ''
  userForm.password = ''
  userForm.is_staff = user.is_staff
  userForm.is_active = user.is_active
  showCreateDialog.value = true
}

const handleResetPassword = (user: User) => {
  ElMessageBox.prompt('请输入新密码', '重置密码', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    inputType: 'password',
    inputValidator: (value: string) => {
      if (!value || value.length < 6) {
        return '密码长度至少6位'
      }
      return true
    }
  }).then(async (ret) => {
    if (!ret?.value) return
    const value = ret.value
    try {
      await usersApi.resetPassword(user.id, value)
      ElMessage.success('密码重置成功')
    } catch (error) {
      console.error('Failed to reset password:', error)
      ElMessage.error('密码重置失败')
    }
  }).catch(() => {})
}

const handleDelete = (user: User) => {
  ElMessageBox.confirm(
    `确定要删除用户 ${user.username} 吗？此操作不可恢复！`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await usersApi.deleteUser(user.id)
      ElMessage.success('删除成功')
      fetchUsers()
    } catch (error) {
      console.error('Failed to delete user:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleSaveUser = async () => {
  if (!userForm.username || !userForm.email) {
    ElMessage.warning('请填写用户名和邮箱')
    return
  }
  
  if (!editingUser.value && !userForm.password) {
    ElMessage.warning('请填写密码')
    return
  }
  
  saving.value = true
  try {
    if (editingUser.value) {
      // 更新用户
      const data: any = {
        username: userForm.username,
        email: userForm.email,
        phone: userForm.phone,
        is_staff: userForm.is_staff,
        is_active: userForm.is_active
      }
      await usersApi.updateUser(userForm.id, data)
      ElMessage.success('更新成功')
    } else {
      // 创建用户
      await usersApi.createUser({
        username: userForm.username,
        email: userForm.email,
        password: userForm.password,
        phone: userForm.phone,
        is_staff: userForm.is_staff,
        is_active: userForm.is_active
      })
      ElMessage.success('创建成功')
    }
    
    showCreateDialog.value = false
    editingUser.value = null
    fetchUsers()
  } catch (error: any) {
    console.error('Failed to save user:', error)
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleDialogClose = () => {
  editingUser.value = null
  userForm.id = 0
  userForm.username = ''
  userForm.email = ''
  userForm.phone = ''
  userForm.password = ''
  userForm.is_staff = false
  userForm.is_active = true
}

watch(showCreateDialog, (open, prev) => {
  if (!open && prev) handleDialogClose()
})

const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  fetchUsers()
})
</script>
