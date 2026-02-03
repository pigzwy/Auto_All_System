<template>
  <div class="space-y-6 p-5">
    <h1 class="text-2xl font-semibold text-foreground">订单管理</h1>

    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="p-6">
        <DataTable :data="orders" v-loading="loading" stripe class="w-full">
        <DataColumn prop="order_no" label="订单号" width="200">
          <template #default="{ row }">
            <span class="font-mono font-semibold text-foreground">{{ row.order_no }}</span>
          </template>
        </DataColumn>
        <DataColumn label="用户" width="150">
          <template #default="{ row }">
            <Tag>{{ row.user_info?.username || row.user }}</Tag>
          </template>
        </DataColumn>
        <DataColumn label="类型" width="100">
          <template #default="{ row }">
            <Tag :type="getOrderTypeColor(row.order_type)">{{ getOrderTypeName(row.order_type) }}</Tag>
          </template>
        </DataColumn>
        <DataColumn label="金额" width="120">
          <template #default="{ row }">
            <span class="text-base font-semibold text-rose-600">¥{{ row.amount }}</span>
          </template>
        </DataColumn>
        <DataColumn label="状态" width="120">
          <template #default="{ row }">
            <Tag :type="getStatusColor(row.status)">{{ getStatusName(row.status) }}</Tag>
          </template>
        </DataColumn>
        <DataColumn label="支付方式" width="120">
          <template #default="{ row }">
            {{ row.payment_method || '-' }}
          </template>
        </DataColumn>
        <DataColumn label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </DataColumn>
        <DataColumn label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <Button text  variant="default" type="button" @click="viewDetail(row)">详情</Button>
            <Button 
              v-if="row.status === 'pending' || row.status === 'processing'" 
              text 
               variant="destructive" type="button" 
              @click="cancelOrder(row)"
            >
              取消
            </Button>
            <Button 
              v-if="row.status === 'paid'" 
              text 
               variant="secondary" type="button" 
              @click="refundOrder(row)"
            >
              退款
            </Button>
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
          @size-change="fetchOrders"
          @current-change="fetchOrders"
        />
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import { paymentsApi, type Order } from '@/api/payments'
import dayjs from 'dayjs'
import { Card, CardContent } from '@/components/ui/card'

const loading = ref(false)
const orders = ref<Order[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const fetchOrders = async () => {
  loading.value = true
  try {
    const response = await paymentsApi.getOrders({
      page: currentPage.value,
      page_size: pageSize.value
    })
    orders.value = response.results
    total.value = response.count
  } catch (error) {
    console.error('Failed to fetch orders:', error)
    ElMessage.error('获取订单失败')
  } finally {
    loading.value = false
  }
}

const getOrderTypeColor = (type: string) => {
  const map: Record<string, any> = {
    recharge: 'success',
    task: 'primary',
    vip: 'warning',
    service_purchase: 'info'
  }
  return map[type] || 'info'
}

const getOrderTypeName = (type: string) => {
  const map: Record<string, string> = {
    recharge: '充值',
    task: '任务',
    vip: 'VIP',
    service_purchase: '服务购买'
  }
  return map[type] || type
}

const getStatusColor = (status: string) => {
  const map: Record<string, any> = {
    pending: 'warning',
    paid: 'success',
    processing: 'primary',
    completed: 'success',
    cancelled: 'danger',
    refunded: 'info'
  }
  return map[status] || 'info'
}

const getStatusName = (status: string) => {
  const map: Record<string, string> = {
    pending: '待支付',
    paid: '已支付',
    processing: '处理中',
    completed: '已完成',
    cancelled: '已取消',
    refunded: '已退款'
  }
  return map[status] || status
}

const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

const viewDetail = (row: Order) => {
  ElMessageBox.alert(
    `
      <div style="text-align: left;">
        <p><strong>订单号：</strong>${row.order_no}</p>
        <p><strong>用户：</strong>${row.user_info.username}</p>
        <p><strong>订单类型：</strong>${getOrderTypeName(row.order_type)}</p>
        <p><strong>金额：</strong>¥${row.amount}</p>
        <p><strong>状态：</strong>${getStatusName(row.status)}</p>
        <p><strong>支付方式：</strong>${row.payment_method || '未支付'}</p>
        <p><strong>描述：</strong>${row.description || '无'}</p>
        <p><strong>创建时间：</strong>${formatDate(row.created_at)}</p>
      </div>
    `,
    '订单详情',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '关闭'
    }
  )
}

const cancelOrder = async (row: Order) => {
  if (row.status !== 'pending' && row.status !== 'processing') {
    ElMessage.warning('只能取消待支付或处理中的订单')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要取消订单 ${row.order_no} 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await paymentsApi.cancelOrder(row.id)
    ElMessage.success('订单已取消')
    fetchOrders()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to cancel order:', error)
      ElMessage.error('取消订单失败')
    }
  }
}

const refundOrder = async (row: Order) => {
  if (row.status !== 'paid') {
    ElMessage.warning('只能退款已支付的订单')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要退款订单 ${row.order_no} 吗？`,
      '警告',
      {
        confirmButtonText: '确定退款',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await paymentsApi.refundOrder(row.id)
    ElMessage.success('退款成功')
    fetchOrders()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('Failed to refund order:', error)
      ElMessage.error('退款失败')
    }
  }
}

onMounted(() => {
  fetchOrders()
})
</script>
