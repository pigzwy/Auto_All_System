<template>
  <Card v-bind="$attrs" :class="cardClass">
    <CardHeader v-if="header || $slots.header" class="pb-3">
      <slot name="header">
        <CardTitle class="text-base">{{ header }}</CardTitle>
      </slot>
    </CardHeader>
    <CardContent>
      <slot />
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const props = defineProps<{
  header?: string
  shadow?: 'always' | 'hover' | 'never'
}>()

const cardClass = computed(() => {
  const base = 'border border-border/80 bg-background/80'
  if (props.shadow === 'never') return base
  if (props.shadow === 'hover') return `${base} shadow-sm transition-shadow hover:shadow-md`
  return `${base} shadow-sm`
})
</script>
