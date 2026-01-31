<template>
  <span
    class="inline-flex items-center justify-center"
    :style="style"
  >
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  size?: number | string
  color?: string
}>()

const style = computed(() => {
  const size = props.size
  const px = typeof size === 'number' ? `${size}px` : size
  return {
    width: px,
    height: px,
    color: props.color,
  }
})
</script>
