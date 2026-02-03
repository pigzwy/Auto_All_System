<template>
  <div :class="wrapperClass">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, provide } from 'vue'

const props = withDefaults(
  defineProps<{
    column?: number
    border?: boolean
  }>(),
  {
    column: 3,
    border: false,
  },
)

provide('el-descriptions-border', props.border)
provide('el-descriptions-cols', props.column)

const wrapperClass = computed(() => {
  const cols = `grid grid-cols-1 md:grid-cols-${props.column}`
  return [cols, 'overflow-hidden rounded-xl border border-border/80 bg-background/70'].filter(Boolean)
})

// props are used directly in computed
</script>
