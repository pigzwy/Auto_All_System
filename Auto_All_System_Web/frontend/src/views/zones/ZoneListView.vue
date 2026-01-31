<template>
  <div class="space-y-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">专区管理</h1>
        <p class="mt-1 text-sm text-muted-foreground">选择一个业务专区进入，或浏览其他环境。</p>
      </div>
    </div>

    <div class="rounded-xl border border-border bg-card text-card-foreground shadow-sm p-6 space-y-10">
      <!-- 业务专区 -->
      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold">🔥 业务专区</h2>
          <span class="text-xs text-muted-foreground">固定入口</span>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <button
            type="button"
            class="group relative w-full text-left rounded-2xl border border-border bg-background/60 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            @click="openGoogleZone"
          >
            <Badge variant="outline" class="absolute right-4 top-4 rounded-full bg-emerald-500/10 text-emerald-700">HOT</Badge>

            <div class="flex items-start gap-4">
              <div class="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center text-2xl">
                🚀
              </div>
              <div class="min-w-0">
                <h3 class="text-base font-semibold text-foreground">Google 业务</h3>
                <p class="mt-1 text-sm text-muted-foreground min-h-[40px]">
                  学生优惠订阅自动化处理
                </p>
              </div>
            </div>

            <div class="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-border/60 bg-muted/30 p-3">
              <div>
                <div class="text-2xl font-semibold leading-none text-foreground">{{ googleStats.accounts }}</div>
                <div class="mt-1 text-xs text-muted-foreground">账号数</div>
              </div>
              <div>
                <div class="text-2xl font-semibold leading-none text-foreground">{{ googleStats.subscribed }}</div>
                <div class="mt-1 text-xs text-muted-foreground">已订阅</div>
              </div>
            </div>

            <div class="mt-4 flex items-center justify-between">
              <Badge variant="outline" class="rounded-full bg-primary/10 text-primary">自动化</Badge>
              <span class="text-sm font-medium text-primary group-hover:underline underline-offset-4">进入</span>
            </div>
          </button>

          <button
            type="button"
            class="group relative w-full text-left rounded-2xl border border-border bg-background/60 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            @click="openGptZone"
          >
            <Badge variant="outline" class="absolute right-4 top-4 rounded-full bg-amber-500/10 text-amber-800">NEW</Badge>

            <div class="flex items-start gap-4">
              <div class="h-12 w-12 rounded-xl bg-emerald-500/12 text-emerald-700 flex items-center justify-center text-2xl">
                🤖
              </div>
              <div class="min-w-0">
                <h3 class="text-base font-semibold text-foreground">GPT 业务</h3>
                <p class="mt-1 text-sm text-muted-foreground min-h-[40px]">
                  OpenAI Team 批量开通/授权自动化
                </p>
              </div>
            </div>

            <div class="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-border/60 bg-muted/30 p-3">
              <div>
                <div class="text-2xl font-semibold leading-none text-foreground">{{ gptStats.teams }}</div>
                <div class="mt-1 text-xs text-muted-foreground">团队数</div>
              </div>
              <div>
                <div class="text-2xl font-semibold leading-none text-foreground">{{ gptStats.accounts }}</div>
                <div class="mt-1 text-xs text-muted-foreground">账号数</div>
              </div>
            </div>

            <div class="mt-4 flex items-center justify-between">
              <Badge variant="outline" class="rounded-full bg-emerald-500/10 text-emerald-700">自动化</Badge>
              <span class="text-sm font-medium text-primary group-hover:underline underline-offset-4">进入</span>
            </div>
          </button>
        </div>
      </section>

      <!-- 其他专区 -->
      <section class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold">📁 其他专区</h2>
          <span class="text-xs text-muted-foreground">{{ zones.length }} 个</span>
        </div>

        <div v-if="zones.length > 0" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <button
            v-for="zone in zones"
            :key="zone.id"
            type="button"
            class="group w-full text-left rounded-2xl border border-border bg-background/60 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            @click="handleZoneClick(zone)"
          >
            <div class="flex items-start gap-4">
              <div class="h-12 w-12 shrink-0 overflow-hidden rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <img
                  v-if="zone.icon"
                  :src="zone.icon"
                  :alt="zone.name"
                  class="h-full w-full object-cover"
                />
                <Icon v-else :size="20"><Grid /></Icon>
              </div>
              <div class="min-w-0 flex-1">
                <h3 class="text-base font-semibold text-foreground truncate">{{ zone.name }}</h3>
                <p class="mt-1 text-sm text-muted-foreground min-h-[40px]">
                  {{ zone.description }}
                </p>
              </div>
            </div>

            <div class="mt-4 flex items-center justify-between">
              <Badge variant="secondary" class="rounded-full">{{ zone.category }}</Badge>
              <span class="text-sm font-semibold text-emerald-600">¥{{ zone.base_price }}/次</span>
            </div>
          </button>
        </div>

        <div v-else-if="loading" class="rounded-xl border border-border bg-muted/20 p-6">
          <div class="flex items-center justify-center text-sm text-muted-foreground">
            <span class="inline-flex items-center gap-2">
              <span class="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-transparent" />
              加载中...
            </span>
          </div>
        </div>

        <div v-else class="rounded-xl border border-border bg-muted/10 p-10 text-center">
          <div class="text-sm font-medium text-foreground">暂无其他专区</div>
          <div class="mt-1 text-xs text-muted-foreground">请稍后再试或联系管理员添加。</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Badge } from '@/components/ui/badge'
import { zonesApi } from '@/api/zones'
import { googleAccountsApi } from '@/api/google'
import { gptBusinessApi } from '@/api/gpt_business'
import type { Zone } from '@/types'

const router = useRouter()
const loading = ref(false)
const zones = ref<Zone[]>([])

const googleStats = reactive({
  accounts: 0,
  subscribed: 0
})

const gptStats = reactive({
  teams: 0,
  accounts: 0
})

const fetchZones = async () => {
  loading.value = true
  try {
    const response = await zonesApi.getZones()
    zones.value = response.results
  } catch (error) {
    console.error('Failed to fetch zones:', error)
  } finally {
    loading.value = false
  }
}

const fetchGoogleStats = async () => {
  try {
    const accountsResponse = await googleAccountsApi.getAccounts({ page_size: 1 })
    googleStats.accounts = accountsResponse.count || 0
    
    const subscribedResponse = await googleAccountsApi.getAccounts({ 
      status: 'subscribed',
      page_size: 1 
    })
    googleStats.subscribed = subscribedResponse.count || 0
  } catch (error) {
    console.error('Failed to fetch Google stats:', error)
  }
}

const fetchGptStats = async () => {
  try {
    const stats = await gptBusinessApi.getStatistics()
    gptStats.teams = stats.teams || 0
    gptStats.accounts = stats.accounts || 0
  } catch (error) {
    // 插件未启用/未安装时可能返回 404
    gptStats.teams = 0
    gptStats.accounts = 0
    console.error('Failed to fetch GPT stats:', error)
  }
}

const handleZoneClick = (zone: Zone) => {
  router.push({ name: 'ZoneDetail', params: { id: zone.id } })
}

const openGoogleZone = () => {
  router.push('/google-zone')
}

const openGptZone = () => {
  router.push('/gpt-zone')
}

onMounted(() => {
  fetchZones()
  fetchGoogleStats()
  fetchGptStats()
})
</script>
