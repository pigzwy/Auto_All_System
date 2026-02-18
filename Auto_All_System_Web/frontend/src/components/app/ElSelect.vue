<template>
  <select
    ref="selectEl"
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
import { ref, onMounted, onBeforeUnmount } from 'vue'

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

const selectEl = ref<HTMLSelectElement | null>(null)

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

// 修复 reka-ui Dialog 焦点陷阱导致 native <select> 需要点两次的问题：
// FocusScope 监听 document 的 focusin/focusout，当 <select> 打开原生下拉时
// 触发 focusout，焦点陷阱把焦点拉回导致下拉关闭。
// 方案：在 select 获得焦点期间，阻止 focusout 事件冒泡到 document，
// 这样 FocusScope 的 handleFocusOut 就不会被触发。
const stopFocusOut = (e: FocusEvent) => {
  e.stopImmediatePropagation()
}

onMounted(() => {
  selectEl.value?.addEventListener('focusout', stopFocusOut, true)
})

onBeforeUnmount(() => {
  selectEl.value?.removeEventListener('focusout', stopFocusOut, true)
})

const { modelValue, placeholder, multiple } = props
</script>
