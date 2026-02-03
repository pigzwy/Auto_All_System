<template>
  <div class="space-y-6 p-5">
    <h1 class="text-2xl font-semibold text-foreground">数据分析</h1>

    <!-- 概览统计 -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <Card v-for="stat in overviewStats" :key="stat.title" class="shadow-sm transition-shadow hover:shadow-md border-border/80 bg-background/80">
        <CardContent class="p-6">
          <div class="flex items-center gap-4">
            <div class="flex h-16 w-16 items-center justify-center rounded-xl" :class="stat.iconClass">
              <Icon :size="32">
                <component :is="stat.icon" />
              </Icon>
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-2xl font-bold leading-none text-foreground">{{ stat.value }}</div>
              <div class="mt-1 text-sm text-muted-foreground">{{ stat.title }}</div>
              <div class="mt-1 text-xs font-semibold" :class="stat.trendClass">{{ stat.trend }}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 图表区域 -->
    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Card class="shadow-sm transition-shadow hover:shadow-md border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">用户增长趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="h-[300px]">
            <div class="flex h-full items-center justify-center rounded-xl border border-border bg-muted/20 text-sm text-muted-foreground">
              📈 图表区域 (可集成ECharts)
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="shadow-sm transition-shadow hover:shadow-md border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">任务完成率</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="h-[300px]">
            <div class="flex h-full items-center justify-center rounded-xl border border-border bg-muted/20 text-sm text-muted-foreground">
              📊 图表区域 (可集成ECharts)
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Card class="shadow-sm transition-shadow hover:shadow-md border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">收入统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="h-[300px]">
            <div class="flex h-full items-center justify-center rounded-xl border border-border bg-muted/20 text-sm text-muted-foreground">
              💰 图表区域 (可集成ECharts)
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="shadow-sm transition-shadow hover:shadow-md border-border/80 bg-background/80">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">专区使用分布</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="h-[300px]">
            <div class="flex h-full items-center justify-center rounded-xl border border-border bg-muted/20 text-sm text-muted-foreground">
              🎯 图表区域 (可集成ECharts)
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { TrendCharts, User, List, Money } from '@/icons'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const overviewStats = ref([
  {
    title: '今日新增用户',
    value: '12',
    trend: '↑ 8.5%',
    trendClass: 'text-emerald-600',
    icon: User,
    iconClass: 'bg-gradient-to-br from-sky-500 to-emerald-500 text-white'
  },
  {
    title: '今日任务数',
    value: '85',
    trend: '↑ 12.3%',
    trendClass: 'text-emerald-600',
    icon: List,
    iconClass: 'bg-gradient-to-br from-emerald-500 to-teal-400 text-white'
  },
  {
    title: '今日收入',
    value: '¥1,250',
    trend: '↑ 5.2%',
    trendClass: 'text-emerald-600',
    icon: Money,
    iconClass: 'bg-gradient-to-br from-amber-500 to-orange-500 text-white'
  },
  {
    title: '任务成功率',
    value: '92.5%',
    trend: '↓ 2.1%',
    trendClass: 'text-rose-600',
    icon: TrendCharts,
    iconClass: 'bg-gradient-to-br from-sky-500 to-cyan-400 text-white'
  }
])
</script>
