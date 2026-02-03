<template>
  <select
    v-bind="$attrs"
    class="flex h-9 w-full rounded-md border border-input bg-background/70 px-3 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
    :multiple="multiple"
    :value="modelValue"
    @change="onChange"
  >
    <option v-if="!multiple" :value="undefined" disabled hidden>
      {{ placeholder || '请选择' }}
    </option>
    <slot />
  </select>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue?: any
    placeholder?: string
    clearable?: boolean
    multiple?: boolean
  }>(),
  {
    placeholder: '',
    clearable: false,
    multiple: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', payload: any): void
  (e: 'change', payload: any): void
}>()

const onChange = (e: Event) => {
  const target = e.target as HTMLSelectElement
  if (props.multiple) {
    const selected = Array.from(target.selectedOptions).map(o => (o as any)._value ?? o.value)
    emit('update:modelValue', selected)
    emit('change', selected)
    return
  }

  const selectedOption = target.selectedOptions[0] as any
  const value = selectedOption?._value
  emit('update:modelValue', value)
  emit('change', value)
}

const { modelValue, placeholder, multiple } = props
</script>
