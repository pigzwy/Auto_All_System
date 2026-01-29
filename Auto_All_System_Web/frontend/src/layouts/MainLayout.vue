<template>
  <div class="flex h-screen w-full bg-gray-50">
    <!-- 侧边栏 -->
    <aside class="flex flex-col w-64 bg-slate-900 text-white transition-all duration-300">
      <!-- Logo -->
      <div class="flex items-center justify-center h-16 border-b border-slate-800">
        <div class="flex items-center gap-2 font-bold text-xl tracking-wide">
          <span class="text-blue-500 text-2xl">⚡</span>
          <span>Auto All</span>
        </div>
      </div>

      <!-- 导航菜单 -->
      <div class="flex-1 overflow-y-auto py-4">
        <el-menu
          :default-active="activeMenu"
          router
          background-color="transparent"
          text-color="#94a3b8"
          active-text-color="#fff"
          class="border-none !border-r-0"
        >
          <el-menu-item index="/" class="hover:bg-slate-800 !my-1 mx-2 !rounded-lg group">
            <el-icon class="group-hover:text-blue-400 transition-colors"><HomeFilled /></el-icon>
            <span class="group-hover:text-white transition-colors">首页</span>
          </el-menu-item>
          
          <div class="px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mt-4 mb-2">
            业务管理
          </div>

          <el-menu-item index="/zones" class="hover:bg-slate-800 !my-1 mx-2 !rounded-lg group">
            <el-icon class="group-hover:text-blue-400 transition-colors"><Grid /></el-icon>
            <span class="group-hover:text-white transition-colors">专区管理</span>
          </el-menu-item>
          <el-menu-item index="/cards" class="hover:bg-slate-800 !my-1 mx-2 !rounded-lg group">
            <el-icon class="group-hover:text-blue-400 transition-colors"><CreditCard /></el-icon>
            <span class="group-hover:text-white transition-colors">虚拟卡</span>
          </el-menu-item>

          <div class="px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mt-4 mb-2">
            账户 & 设置
          </div>

          <el-menu-item index="/balance" class="hover:bg-slate-800 !my-1 mx-2 !rounded-lg group">
            <el-icon class="group-hover:text-blue-400 transition-colors"><Wallet /></el-icon>
            <span class="group-hover:text-white transition-colors">余额管理</span>
          </el-menu-item>
          <el-menu-item index="/recharge" class="hover:bg-slate-800 !my-1 mx-2 !rounded-lg group">
            <el-icon class="group-hover:text-blue-400 transition-colors"><Money /></el-icon>
            <span class="group-hover:text-white transition-colors">账户充值</span>
          </el-menu-item>
          <el-menu-item index="/vip" class="hover:bg-slate-800 !my-1 mx-2 !rounded-lg group">
            <el-icon class="group-hover:text-blue-400 transition-colors"><Star /></el-icon>
            <span class="group-hover:text-white transition-colors">VIP会员</span>
          </el-menu-item>
          <el-menu-item index="/profile" class="hover:bg-slate-800 !my-1 mx-2 !rounded-lg group">
            <el-icon class="group-hover:text-blue-400 transition-colors"><User /></el-icon>
            <span class="group-hover:text-white transition-colors">个人中心</span>
          </el-menu-item>
          
          <el-menu-item 
            v-if="userStore.user?.is_staff" 
            index="/admin" 
            class="!my-1 mx-2 !rounded-lg mt-6 !text-white"
            style="background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);"
          >
            <el-icon><Setting /></el-icon>
            <span class="font-bold">管理后台</span>
          </el-menu-item>
        </el-menu>
      </div>
      
      <!-- 用户简略信息 (底部) -->
      <div class="p-4 border-t border-slate-800 bg-slate-900/50">
        <div class="flex items-center gap-3">
          <el-avatar :size="32" :src="userStore.user?.avatar || undefined" class="!bg-blue-600 font-bold">
            {{ userStore.user?.username?.[0]?.toUpperCase() }}
          </el-avatar>
          <div class="flex flex-col overflow-hidden">
            <span class="text-sm font-medium text-white truncate">{{ userStore.user?.username }}</span>
            <span class="text-xs text-slate-400 truncate">VIP {{ userStore.user?.vip_level || 0 }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部导航栏 -->
      <header class="h-16 bg-white border-b border-gray-100 flex items-center justify-between px-6 shadow-sm z-10">
        <div class="flex items-center">
          <el-breadcrumb separator="/" class="!text-sm">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRouteName">{{ currentRouteName }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="flex items-center gap-4">
          <!-- 通知铃铛 (示例) -->
          <div class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 cursor-pointer text-gray-500 transition-colors relative">
            <el-icon :size="18"><Bell /></el-icon>
            <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
          </div>

          <el-dropdown @command="handleCommand" trigger="click">
            <span class="flex items-center gap-2 cursor-pointer hover:bg-gray-50 px-2 py-1 rounded-lg transition-colors">
              <el-avatar :size="32" :src="userStore.user?.avatar || undefined" class="!bg-blue-100 !text-blue-600 border border-blue-200">
                {{ userStore.user?.username?.[0]?.toUpperCase() }}
              </el-avatar>
              <div class="hidden md:flex flex-col items-start">
                <span class="text-sm font-medium text-gray-700 leading-none">{{ userStore.user?.username }}</span>
                <span class="text-xs text-gray-400 mt-1">余额: ¥{{ userStore.user?.balance || '0.00' }}</span>
              </div>
              <el-icon class="text-gray-400"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu class="!p-2 min-w-[160px]">
                <div class="px-4 py-2 border-b border-gray-100 mb-1">
                  <div class="text-sm font-bold text-gray-800">我的账户</div>
                  <div class="text-xs text-gray-400 mt-0.5">{{ userStore.user?.email }}</div>
                </div>
                <el-dropdown-item command="profile" class="!rounded-md">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item v-if="userStore.user?.is_staff" command="admin" class="!rounded-md">
                  <el-icon><Setting /></el-icon>管理后台
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided class="!text-red-500 hover:!bg-red-50 !rounded-md">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区域 -->
      <main class="flex-1 overflow-auto bg-gray-50 p-6">
        <div class="max-w-7xl mx-auto">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { 
  Setting, Money, Star, HomeFilled, Grid, CreditCard, 
  Wallet, User, ArrowDown, Bell, SwitchButton 
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const currentRouteName = computed(() => route.meta?.title || route.name as string)

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await userStore.logout()
      ElMessage.success('退出成功')
      router.push({ name: 'Login' })
    } catch (error) {
      console.error('Logout error:', error)
    }
  } else if (command === 'profile') {
    router.push({ name: 'Profile' })
  } else if (command === 'admin') {
    router.push({ name: 'AdminDashboard' })
  }
}
</script>

<style scoped>
/* 覆盖 Element Plus 菜单默认样式以适配 Dark Mode */
:deep(.el-menu-item.is-active) {
  background-color: #3b82f6 !important;
  color: #fff !important;
}

:deep(.el-menu-item:hover) {
  background-color: #1e293b !important; /* slate-800 */
}

/* 页面切换动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
