<template>
  <div class="gpt-business-zone">
    <div class="topbar">
      <div class="left">
        <el-button text @click="goZones">
          <el-icon><Back /></el-icon>
          返回专区
        </el-button>
        <div class="title">
          <div class="title-main">GPT 业务专区</div>
          <div class="title-sub">OpenAI Team 自动开通 / 授权</div>
        </div>
      </div>

      <div class="right">
        <el-tag size="small" type="success">Beta</el-tag>
        <el-dropdown>
          <span class="user">
            <el-icon><User /></el-icon>
            <span class="name">{{ userStore.user?.username || '用户' }}</span>
            <el-icon class="chevron"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="goProfile">个人资料</el-dropdown-item>
              <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="body">
      <aside class="sidebar">
        <el-menu
          :default-active="activeModule"
          class="menu"
          @select="handleSelect"
        >
          <el-menu-item index="workstation">
            <el-icon><Monitor /></el-icon>
            <span>工作台</span>
          </el-menu-item>

          <el-menu-item index="accounts">
            <el-icon><Avatar /></el-icon>
            <span>账号列表</span>
          </el-menu-item>
        </el-menu>
      </aside>

      <main class="content">
        <component :is="currentModule" />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Back, User, ArrowDown, Monitor, Avatar } from '@element-plus/icons-vue'

import WorkstationModule from './gpt-modules/WorkstationModule.vue'
import AccountsModule from './gpt-modules/AccountsModule.vue'

type ModuleKey = 'workstation' | 'accounts'

const router = useRouter()
const userStore = useUserStore()

const activeModule = ref<ModuleKey>('workstation')

const currentModule = computed(() => {
  if (activeModule.value === 'workstation') return WorkstationModule
  if (activeModule.value === 'accounts') return AccountsModule
  return WorkstationModule
})

const handleSelect = (index: string) => {
  activeModule.value = index as ModuleKey
}

const goZones = () => {
  router.push('/zones')
}

const goProfile = () => {
  router.push('/profile')
}

const logout = async () => {
  await userStore.logout()
  router.replace('/login')
}
</script>

<style scoped lang="scss">
.gpt-business-zone {
  min-height: 100vh;
  background: radial-gradient(1200px 500px at 20% 0%, rgba(16, 185, 129, 0.10), transparent 50%),
    radial-gradient(900px 480px at 90% 10%, rgba(6, 182, 212, 0.10), transparent 55%),
    #f7f8fa;

  .topbar {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    border-bottom: 1px solid #ebeef5;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(8px);

    .left {
      display: flex;
      align-items: center;
      gap: 12px;

      .title {
        display: flex;
        flex-direction: column;
        line-height: 1.1;

        .title-main {
          font-size: 16px;
          font-weight: 700;
          color: #111827;
        }

        .title-sub {
          font-size: 12px;
          color: #6b7280;
        }
      }
    }

    .right {
      display: flex;
      align-items: center;
      gap: 12px;

      .user {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        cursor: pointer;
        color: #374151;

        .name {
          max-width: 140px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .chevron {
          font-size: 12px;
          opacity: 0.8;
        }
      }
    }
  }

  .body {
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 16px;
    padding: 16px;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }

  .sidebar {
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid #ebeef5;
    border-radius: 10px;
    overflow: hidden;

    .menu {
      border-right: none;
    }
  }

  .content {
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid #ebeef5;
    border-radius: 10px;
    padding: 16px;
  }
}
</style>
