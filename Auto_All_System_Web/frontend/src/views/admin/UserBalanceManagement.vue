<template>
  <div class="space-y-6 p-5">
    <h1 class="text-2xl font-semibold text-foreground">用户余额管理</h1>

    <Card class="shadow-sm">
      <CardContent class="p-6">
        <DataTable :data="balances" v-loading="loading" stripe class="w-full">
        <DataColumn prop="user" label="用户" width="150">
          <template #default="{ row }">
            <Tag>{{ row.user_info?.username || row.user }}</Tag>
          </template>
        </DataColumn>
        <DataColumn label="余额" width="150">
          <template #default="{ row }">
            <span class="text-lg font-semibold text-emerald-600">¥{{ row.balance }}</span>
          </template>
        </DataColumn>
        <DataColumn label="冻结金额" width="150">
          <template #default="{ row }">
            <span class="text-amber-600">¥{{ row.frozen_amount }}</span>
          </template>
        </DataColumn>
        <DataColumn label="可用余额" width="150">
          <template #default="{ row }">
            <span class="font-semibold text-primary">¥{{ row.available_balance }}</span>
          </template>
        </DataColumn>
        <DataColumn prop="currency" label="货币" width="80" />
        <DataColumn prop="updated_at" label="最后更新" width="180" />
        <DataColumn label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <Button text  variant="default" type="button" @click="showRecharge(row)">充值</Button>
            <Button text  variant="secondary" type="button" @click="showFreeze(row)">冻结</Button>
            <Button text @click="viewLogs(row)">日志</Button>
          </template>
        </DataColumn>
        </DataTable>

        <Paginator
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          class="mt-5 justify-center"
          @size-change="fetchBalances"
          @current-change="fetchBalances"
        />
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import usersApi, { type UserBalance } from '@/api/users'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const balances = ref<UserBalance[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

const fetchBalances = async () => {
  loading.value = true
  try {
    const response = await usersApi.getUserBalances({
      page: currentPage.value,
      page_size: pageSize.value
    })
    balances.value = response.results
    total.value = response.count
  } catch (error) {
    console.error('Failed to fetch balances:', error)
    ElMessage.error('获取余额列表失败')
  } finally {
    loading.value = false
  }
}

const showRecharge = (_row: UserBalance) => {
  ElMessage.info('充值功能开发中')
}

const showFreeze = (_row: UserBalance) => {
  ElMessage.info('冻结功能开发中')
}

const viewLogs = (_row: UserBalance) => {
  ElMessage.info('查看日志')
}

onMounted(() => {
  fetchBalances()
})
</script>
