<template>
  <span :title="contentText" class="inline-flex">
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ content?: string }>()

const contentText = computed(() => props.content ?? '')
</script>
