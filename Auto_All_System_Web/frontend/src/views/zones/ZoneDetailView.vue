<template>
  <div v-loading="loading" class="space-y-6">
    <Card class="shadow-sm">
      <CardContent class="px-4 py-3">
        <PageHeader @back="$router.back()">
          <template #content>
            <span class="text-base font-semibold text-foreground">{{ zone?.name || '专区详情' }}</span>
          </template>
        </PageHeader>
      </CardContent>
    </Card>

    <Card v-if="zone" class="shadow-sm">
      <CardContent class="p-6">
        <div class="space-y-3">
          <div>
            <h2 class="text-lg font-semibold text-foreground">{{ zone.name }}</h2>
            <p class="mt-1 text-sm text-muted-foreground">{{ zone.description }}</p>
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <Badge variant="secondary" class="rounded-full">{{ zone.category }}</Badge>
            <span class="inline-flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1 text-sm">
              基础价格 <span class="font-semibold text-emerald-600">¥{{ zone.base_price }}</span>
            </span>
            <span class="inline-flex items-center gap-2 rounded-full border border-border bg-muted/30 px-3 py-1 text-sm">
              最低余额 <span class="font-semibold text-amber-600">¥{{ zone.min_balance }}</span>
            </span>
          </div>
        </div>
      </CardContent>
    </Card>

    <Card class="shadow-sm">
      <CardHeader class="pb-3">
        <div class="flex items-center justify-between">
          <CardTitle class="text-base">专区配置</CardTitle>
          <span class="text-xs text-muted-foreground">{{ configs.length }} 项</span>
        </div>
      </CardHeader>
      <CardContent>
        <Descriptions :column="1" border>
        <DescriptionsItem
          v-for="config in configs"
          :key="config.id"
          :label="config.config_key"
        >
          <span class="text-sm text-foreground break-all">{{ formatConfigValue(config) }}</span>
          <TooltipText v-if="config.description" :content="config.description" placement="top">
            <Icon class="ml-2 text-muted-foreground"><QuestionFilled /></Icon>
          </TooltipText>
        </DescriptionsItem>
        </Descriptions>
      </CardContent>
    </Card>

    <Card class="shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">创建任务</CardTitle>
      </CardHeader>
      <CardContent>
          <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <p class="text-sm text-muted-foreground">从当前专区快速创建一个新任务。</p>
            <Button variant="success" type="button" @click="handleCreateTask">
              <Icon><Plus /></Icon>
              创建新任务
            </Button>
          </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { zonesApi } from '@/api/zones'
import type { Zone, ZoneConfig } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const zone = ref<Zone | null>(null)
const configs = ref<ZoneConfig[]>([])

const fetchZoneDetail = async () => {
  loading.value = true
  try {
    const zoneId = Number(route.params.id)
    zone.value = await zonesApi.getZone(zoneId)
    configs.value = await zonesApi.getZoneConfig(zoneId)
  } catch (error) {
    console.error('Failed to fetch zone detail:', error)
  } finally {
    loading.value = false
  }
}

const formatConfigValue = (config: ZoneConfig) => {
  if (typeof config.config_value === 'object') {
    return JSON.stringify(config.config_value)
  }
  return String(config.config_value)
}

const handleCreateTask = () => {
  router.push({
    name: 'Tasks',
    query: { zone_id: zone.value?.id }
  })
}

onMounted(() => {
  fetchZoneDetail()
})
</script>
