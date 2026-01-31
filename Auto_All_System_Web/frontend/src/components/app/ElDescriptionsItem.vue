<template>
  <div class="border-b border-border md:border-b-0 md:border-r border-border">
    <div class="grid grid-cols-[140px_1fr]">
      <div class="bg-muted/20 px-3 py-2 text-sm font-medium text-muted-foreground">
        {{ label }}
      </div>
      <div class="px-3 py-2 text-sm text-foreground">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string }>()
</script>
