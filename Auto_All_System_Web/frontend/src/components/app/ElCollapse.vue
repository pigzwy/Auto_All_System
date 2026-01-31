<template>
  <Accordion
    :type="accordion ? 'single' : 'multiple'"
    :collapsible="true"
    :model-value="accordion ? (modelValue || undefined) : (Array.isArray(modelValue) ? modelValue : modelValue ? [modelValue] : [])"
    @update:model-value="onUpdate"
  >
    <slot />
  </Accordion>
</template>

<script setup lang="ts">
import { Accordion } from '@/components/ui/accordion'

const props = withDefaults(
  defineProps<{
    modelValue: string | string[]
    accordion?: boolean
  }>(),
  {
    accordion: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', payload: any): void
}>()

const onUpdate = (val: any) => {
  if (props.accordion) {
    emit('update:modelValue', val || '')
    return
  }
  emit('update:modelValue', Array.isArray(val) ? val : val ? [val] : [])
}

const { modelValue, accordion } = props
</script>
