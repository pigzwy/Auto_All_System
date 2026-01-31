<template>
  <Switch
    :checked="Boolean(modelValue)"
    :disabled="disabled"
    @update:checked="onUpdate"
  />
</template>

<script setup lang="ts">
import { Switch } from '@/components/ui/switch'

const props = defineProps<{
  modelValue?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', payload: boolean): void
  (e: 'change', payload: boolean): void
}>()

const onUpdate = (val: boolean) => {
  emit('update:modelValue', val)
  emit('change', val)
}

const { modelValue, disabled } = props
</script>
