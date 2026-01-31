<template>
  <div :class="wrapperClass">
    <label v-if="label" :class="labelClass">{{ label }}</label>
    <div class="min-w-0 flex-1">
      <slot />
      <p v-if="error" class="mt-1 text-xs text-rose-600">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { elFormKey } from './symbols'
import { inject } from 'vue'

const props = defineProps<{
  label?: string
  prop?: string
  required?: boolean
}>()

const form = inject(elFormKey, null)
const error = ref('')

const itemCtx = {
  prop: props.prop,
  setError: (msg: string) => {
    error.value = msg
  },
  clearError: () => {
    error.value = ''
  },
}

onMounted(() => {
  form?.registerItem(itemCtx)
})

onBeforeUnmount(() => {
  form?.unregisterItem(itemCtx)
})

const wrapperClass = computed(() => {
  if (form?.inline) return 'flex items-center gap-2'
  return 'grid gap-1'
})

const labelClass = computed(() => {
  if (form?.inline) return 'text-sm text-muted-foreground whitespace-nowrap'
  return 'text-sm font-medium text-foreground'
})

const { label } = props
</script>
