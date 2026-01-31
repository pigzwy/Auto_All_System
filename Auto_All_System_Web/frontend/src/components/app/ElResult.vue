<template>
  <div class="rounded-lg border border-border bg-background p-6 text-center">
    <div class="text-lg font-semibold text-foreground">{{ title }}</div>
    <div v-if="subTitle" class="mt-2 text-sm text-muted-foreground">{{ subTitle }}</div>
    <div v-if="$slots.extra" class="mt-4">
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon?: string
  title?: string
  subTitle?: string
}>()
</script>
