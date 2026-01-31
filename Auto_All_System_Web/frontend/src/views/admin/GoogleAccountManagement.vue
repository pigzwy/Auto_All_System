<template>
  <div class="space-y-6 p-5">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">Google账号管理</h1>
        <p class="mt-1 text-sm text-muted-foreground">管理账号状态、Gemini 订阅、2FA 等信息。</p>
      </div>
      <Button variant="success" type="button" @click="showDialog = true">
        <Icon><Plus /></Icon>
        添加账号
      </Button>
    </div>

    <Card class="shadow-sm">
      <CardContent class="p-6">
      <DataTable :data="accounts" v-loading="loading" stripe class="w-full">
        <DataColumn prop="id" label="ID" width="60" />
        <DataColumn prop="email" label="邮箱" width="250">
          <template #default="{ row }">
            <span class="font-semibold text-foreground">📧 {{ row.email }}</span>
          </template>
        </DataColumn>
        <DataColumn label="状态" width="100">
          <template #default="{ row }">
            <Tag :type="getStatusColor(row.status)">{{ getStatusName(row.status) }}</Tag>
          </template>
        </DataColumn>
        <DataColumn label="Gemini" width="100">
          <template #default="{ row }">
            <Tag :type="getGeminiColor(row.gemini_status)">{{ getGeminiName(row.gemini_status) }}</Tag>
          </template>
        </DataColumn>
        <DataColumn label="2FA" width="80">
          <template #default="{ row }">
            {{ row.two_fa_secret ? '🔒' : '🔓' }}
          </template>
        </DataColumn>
        <DataColumn label="订阅到期" width="120">
          <template #default="{ row }">
            {{ row.subscription_end_date || '-' }}
          </template>
        </DataColumn>
        <DataColumn prop="created_at" label="创建时间" width="180" />
        <DataColumn label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <Button text variant="ghost" class="text-warning hover:text-warning" type="button" @click="editAccount(row)">编辑</Button>
            <Button text  variant="default" type="button" @click="testLogin(row)">测试登录</Button>
            <Button text  variant="destructive" type="button" @click="deleteAccount(row)">删除</Button>
          </template>
        </DataColumn>
      </DataTable>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { Plus } from '@/icons'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const accounts = ref([])
const showDialog = ref(false)

const fetchAccounts = async () => {
  loading.value = true
  try {
    // TODO: 调用Google账号API
    accounts.value = []
  } catch (error) {
    ElMessage.error('获取账号列表失败')
  } finally {
    loading.value = false
  }
}

const getStatusColor = (status: string) => {
  const map: Record<string, any> = {
    active: 'success',
    locked: 'danger',
    disabled: 'info'
  }
  return map[status] || 'info'
}

const getStatusName = (status: string) => {
  const map: Record<string, string> = {
    active: '正常',
    locked: '锁定',
    disabled: '停用'
  }
  return map[status] || status
}

const getGeminiColor = (status: string) => {
  const map: Record<string, any> = {
    not_subscribed: 'info',
    pending: 'warning',
    active: 'success',
    expired: 'danger'
  }
  return map[status] || 'info'
}

const getGeminiName = (status: string) => {
  const map: Record<string, string> = {
    not_subscribed: '未订阅',
    pending: '订阅中',
    active: '已订阅',
    expired: '已过期'
  }
  return map[status] || status
}

const editAccount = (_row: any) => {
  ElMessage.info('编辑功能开发中')
}

const testLogin = (_row: any) => {
  ElMessage.info('测试登录功能开发中')
}

const deleteAccount = (_row: any) => {
  ElMessage.info('删除功能开发中')
}

onMounted(() => {
  fetchAccounts()
})
</script>
