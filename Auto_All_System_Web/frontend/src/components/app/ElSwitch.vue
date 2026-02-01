<template>
  <Switch
    :model-value="Boolean(props.modelValue)"
    :disabled="props.disabled"
    @update:modelValue="onUpdate"
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
  (e: 'update:model-value', payload: boolean): void
  (e: 'change', payload: boolean): void
}>()

const onUpdate = (val: boolean) => {
  emit('update:modelValue', val)
  // Some callers listen in kebab-case (DOM-attr compatible)
  emit('update:model-value', val)
  emit('change', val)
}
</script>
