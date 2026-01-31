<template>
  <div class="space-y-1">
    <div class="text-xs text-muted-foreground">{{ title }}</div>
    <div class="text-2xl font-bold leading-none text-foreground">
      <slot name="prefix" />
      {{ value }}
      <span v-if="suffix" class="ml-1 text-sm text-muted-foreground">{{ suffix }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  value?: string | number
  suffix?: string
}>()
</script>
