<template>
  <div class="min-h-screen bg-muted/30 text-foreground">
    <header class="sticky top-0 z-30 bg-background/80 backdrop-blur border-b border-border">
      <div class="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3 min-w-0">
          <Button variant="ghost" size="sm" class="gap-2" @click="goZones">
            <ChevronLeft class="h-4 w-4" />
            返回专区
          </Button>
          <div class="min-w-0">
            <div class="text-sm font-semibold text-foreground">GPT 业务专区</div>
            <div class="text-xs text-muted-foreground truncate">OpenAI Team 自动开通 / 授权</div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <Badge variant="secondary" class="rounded-full">Beta</Badge>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="outline" size="sm" class="gap-2 bg-muted/30">
                <UserRound class="h-4 w-4 text-muted-foreground" />
                <span class="max-w-[140px] truncate">{{ userStore.user?.username || '用户' }}</span>
                <ChevronDown class="h-4 w-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" class="w-44">
              <DropdownMenuItem @select="goProfile">
                个人资料
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="text-destructive" @select="logout">
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>

    <div class="mx-auto max-w-7xl p-4 grid gap-4 md:grid-cols-[220px_1fr] items-start">
      <aside class="rounded-xl border border-border bg-card text-card-foreground shadow-sm overflow-hidden md:sticky md:top-20">
        <nav class="p-2 space-y-1">
          <Button
            variant="ghost"
            class="w-full justify-start gap-2"
            :class="activeModule === 'workstation' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'"
            @click="handleSelect('workstation')"
          >
            <LayoutDashboard class="h-4 w-4" />
            工作台
          </Button>

          <Button
            variant="ghost"
            class="w-full justify-start gap-2"
            :class="activeModule === 'accounts' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'"
            @click="handleSelect('accounts')"
          >
            <Users class="h-4 w-4" />
            账号列表
          </Button>
        </nav>
      </aside>

      <main class="min-w-0 rounded-xl border border-border bg-card text-card-foreground shadow-sm">
        <div class="p-4 min-w-0">
          <div class="min-w-0 overflow-x-auto">
            <component :is="currentModule" />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ChevronDown, ChevronLeft, LayoutDashboard, UserRound, Users } from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

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

