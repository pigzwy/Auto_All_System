<template>
  <div class="rounded-lg border border-border bg-muted/10 p-4">
    <div class="text-sm text-foreground">
      <slot name="title">
        <strong v-if="title">{{ title }}</strong>
      </slot>
    </div>
    <div v-if="$slots.default" class="mt-2 text-sm text-muted-foreground">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  type?: string
  title?: string
  closable?: boolean
}>()
</script>
