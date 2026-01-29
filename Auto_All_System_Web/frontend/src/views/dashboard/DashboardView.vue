<template>
  <div class="space-y-6">
    <!-- 顶部欢迎栏 -->
    <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex items-center justify-between relative overflow-hidden">
      <div class="relative z-10">
        <h1 class="text-2xl font-bold text-gray-800 mb-2">
          早安, {{ userStore.user?.username || '用户' }} 👋
        </h1>
        <p class="text-gray-500 text-sm">
          这里是您的自动化控制中心，今日系统运行正常。
        </p>
      </div>
      <!-- 装饰背景 -->
      <div class="absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-blue-50 to-transparent pointer-events-none"></div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- 余额卡片 -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-300 relative group overflow-hidden">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">账户余额</span>
          <div class="p-2 bg-blue-50 text-blue-600 rounded-lg group-hover:scale-110 transition-transform">
            <el-icon :size="20"><Wallet /></el-icon>
          </div>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-bold text-gray-800">¥{{ balance?.balance || '0.00' }}</span>
          <span class="text-xs text-green-500 bg-green-50 px-2 py-0.5 rounded-full flex items-center gap-1">
            <el-icon><Top /></el-icon> 正常
          </span>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-50 flex gap-2">
           <button @click="$router.push('/recharge')" class="flex-1 text-xs bg-gray-50 hover:bg-gray-100 text-gray-600 py-1.5 rounded transition-colors">
             充值
           </button>
           <button @click="$router.push('/balance')" class="flex-1 text-xs bg-gray-50 hover:bg-gray-100 text-gray-600 py-1.5 rounded transition-colors">
             明细
           </button>
        </div>
      </div>

      <!-- 专区卡片 -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-300 group">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">可用专区</span>
          <div class="p-2 bg-orange-50 text-orange-500 rounded-lg group-hover:scale-110 transition-transform">
            <el-icon :size="20"><Grid /></el-icon>
          </div>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-bold text-gray-800">{{ zones.length || 0 }}</span>
          <span class="text-sm text-gray-400">个活跃环境</span>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-50 text-xs text-gray-400">
          最近访问: {{ zones[0]?.name || '无' }}
        </div>
      </div>

      <!-- 虚拟卡卡片 -->
      <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow duration-300 group">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">虚拟卡资源</span>
          <div class="p-2 bg-red-50 text-red-500 rounded-lg group-hover:scale-110 transition-transform">
            <el-icon :size="20"><CreditCard /></el-icon>
          </div>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-bold text-gray-800">{{ cardCount || 0 }}</span>
          <span class="text-sm text-gray-400">张可用</span>
        </div>
        <div class="mt-4 pt-4 border-t border-gray-50">
          <div class="w-full bg-gray-100 rounded-full h-1.5 mb-1 overflow-hidden">
            <div class="bg-red-500 h-1.5 rounded-full" style="width: 70%"></div>
          </div>
          <div class="flex justify-between text-xs text-gray-400">
            <span>使用率</span>
            <span>70%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速操作区 -->
    <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <h3 class="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
        <span class="w-1 h-6 bg-blue-500 rounded-full"></span>
        快速操作
      </h3>
      
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div @click="$router.push('/zones')" class="group cursor-pointer p-4 rounded-xl border border-gray-100 hover:border-blue-200 hover:bg-blue-50/50 transition-all duration-300 flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            <el-icon :size="24"><Grid /></el-icon>
          </div>
          <span class="text-sm font-medium text-gray-700 group-hover:text-blue-600">浏览专区</span>
        </div>

        <div @click="$router.push('/cards')" class="group cursor-pointer p-4 rounded-xl border border-gray-100 hover:border-purple-200 hover:bg-purple-50/50 transition-all duration-300 flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            <el-icon :size="24"><CreditCard /></el-icon>
          </div>
          <span class="text-sm font-medium text-gray-700 group-hover:text-purple-600">管理卡片</span>
        </div>

        <div @click="$router.push('/balance')" class="group cursor-pointer p-4 rounded-xl border border-gray-100 hover:border-green-200 hover:bg-green-50/50 transition-all duration-300 flex flex-col items-center justify-center gap-3">
          <div class="w-12 h-12 rounded-full bg-green-100 text-green-600 flex items-center justify-center group-hover:scale-110 transition-transform shadow-sm">
            <el-icon :size="24"><Money /></el-icon>
          </div>
          <span class="text-sm font-medium text-gray-700 group-hover:text-green-600">账户充值</span>
        </div>

        <div class="group cursor-pointer p-4 rounded-xl border border-gray-100 hover:border-orange-200 hover:bg-orange-50/50 transition-all duration-300 flex flex-col items-center justify-center gap-3 opacity-60">
           <div class="w-12 h-12 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center shadow-inner">
            <el-icon :size="24"><Plus /></el-icon>
          </div>
          <span class="text-sm font-medium text-gray-500">更多功能</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { balanceApi } from '@/api/balance'
import { zonesApi } from '@/api/zones'
import { cardsApi } from '@/api/cards'
import { useUserStore } from '@/stores/user'
import { 
  Wallet, Grid, CreditCard, Money, Top, Plus 
} from '@element-plus/icons-vue'
import type { UserBalance, Zone } from '@/types'

const userStore = useUserStore()
const loading = ref(false)
const balance = ref<UserBalance | null>(null)
const zones = ref<Zone[]>([])
const cardCount = ref(0)

const fetchData = async () => {
  loading.value = true
  try {
    // 获取余额
    balance.value = await balanceApi.getMyBalance()

    // 获取专区
    const zonesResponse = await zonesApi.getZones()
    zones.value = zonesResponse.results

    // 获取虚拟卡数量
    const cardsResponse = await cardsApi.getMyCards()
    cardCount.value = cardsResponse.length
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
/* 可以在这里添加一些特殊的动画效果 */
</style>
