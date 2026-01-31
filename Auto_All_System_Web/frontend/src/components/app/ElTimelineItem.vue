<template>
  <div class="relative pl-5">
    <div class="absolute left-2 top-1.5 h-full w-px bg-border" />
    <div class="absolute left-[6px] top-1.5 h-2.5 w-2.5 rounded-full" :class="dotClass" />
    <div class="flex items-start justify-between gap-4">
      <div class="min-w-0">
        <slot />
      </div>
      <span v-if="timestamp" class="shrink-0 text-xs text-muted-foreground">{{ timestamp }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ timestamp?: string; type?: string; color?: string }>()

const dotClass = computed(() => {
  if (props.color) return ''
  if (props.type === 'success') return 'bg-emerald-500'
  if (props.type === 'danger') return 'bg-rose-500'
  if (props.type === 'warning') return 'bg-amber-500'
  return 'bg-primary/60'
})
</script>
