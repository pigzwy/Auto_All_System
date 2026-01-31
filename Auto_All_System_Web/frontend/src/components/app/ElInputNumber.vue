<template>
  <Input
    v-bind="$attrs"
    type="number"
    :model-value="modelValue ?? ''"
    @update:modelValue="onUpdate"
  />
</template>

<script setup lang="ts">
import { Input } from '@/components/ui/input'

const props = defineProps<{
  modelValue?: number | null
  min?: number
  max?: number
  step?: number
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', payload: number | null): void
  (e: 'change', payload: number | null): void
}>()

const onUpdate = (val: string | number) => {
  const n = typeof val === 'number' ? val : Number(val)
  const next = Number.isFinite(n) ? n : null
  emit('update:modelValue', next)
  emit('change', next)
}

const { modelValue } = props
</script>
