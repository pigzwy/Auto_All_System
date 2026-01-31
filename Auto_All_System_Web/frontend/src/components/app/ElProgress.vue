<template>
  <div class="w-full">
    <Progress :model-value="percentage" />
    <div v-if="$slots.default" class="mt-2 text-xs text-muted-foreground">
      <slot :percentage="percentage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Progress } from '@/components/ui/progress'

defineProps<{
  percentage: number
  status?: string
  strokeWidth?: number
}>()
</script>
