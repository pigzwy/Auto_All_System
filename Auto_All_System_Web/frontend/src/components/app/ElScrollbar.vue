<template>
  <div class="overflow-auto" :style="style">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ height?: string | number }>()

const style = computed(() => {
  if (!props.height) return undefined
  const h = typeof props.height === 'number' ? `${props.height}px` : props.height
  return { height: h }
})
</script>
