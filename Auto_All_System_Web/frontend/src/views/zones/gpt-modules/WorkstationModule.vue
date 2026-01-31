<script setup lang="ts">
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-2xl font-semibold text-foreground">工作台</h2>
    </div>
    
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <!-- Placeholder stats -->
      <Card class="bg-card text-card-foreground">
        <CardContent class="p-6">
          <div class="text-sm font-medium text-muted-foreground">总账号数</div>
          <div class="mt-2 text-2xl font-bold">0</div>
        </CardContent>
      </Card>
    </div>

    <Card class="bg-card text-card-foreground">
      <CardHeader>
        <CardTitle>最近活动</CardTitle>
        <CardDescription>暂无数据</CardDescription>
      </CardHeader>
      <CardContent>
        <div class="h-[200px] w-full rounded-md border border-dashed border-border bg-muted/30 flex items-center justify-center text-muted-foreground text-sm">
          图表占位符
        </div>
      </CardContent>
    </Card>
  </div>
</template>

