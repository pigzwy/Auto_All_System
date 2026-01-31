<template>
  <label class="inline-flex items-center gap-2 text-sm">
    <input type="radio" class="h-4 w-4" :checked="isActive" @change="select" />
    <span><slot /></span>
  </label>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'

const props = defineProps<{ label: string | number }>()
const group = inject('el-radio-group', null) as null | {
  modelValue: () => string | number
  setValue: (val: string | number) => void
}

const isActive = computed(() => group?.modelValue() === props.label)
const select = () => group?.setValue(props.label)
</script>
