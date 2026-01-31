<template>
  <div class="inline-flex items-center gap-2">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { provide } from 'vue'

const props = defineProps<{ modelValue: string | number }>()
const emit = defineEmits<{ (e: 'update:modelValue', payload: string | number): void; (e: 'change', payload: string | number): void }>()

provide('el-radio-group', {
  modelValue: () => props.modelValue,
  setValue: (val: string | number) => {
    emit('update:modelValue', val)
    emit('change', val)
  },
})

// modelValue is consumed via provided getters
</script>
