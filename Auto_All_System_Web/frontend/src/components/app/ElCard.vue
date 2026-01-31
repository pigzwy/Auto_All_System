<template>
  <Card v-bind="$attrs" class="shadow-sm">
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

defineProps<{
  header?: string
  shadow?: 'always' | 'hover' | 'never'
}>()
</script>
