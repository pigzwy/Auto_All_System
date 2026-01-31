<template>
  <span :class="wrapperClass">
    <slot />
    <button
      v-if="closable"
      type="button"
      class="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-sm hover:bg-black/10"
      @click="$emit('close')"
    >
      <span class="text-xs leading-none">×</span>
    </button>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'success' | 'warning' | 'danger' | 'info'
    size?: 'small' | 'default' | 'large'
    closable?: boolean
  }>(),
  {
    type: 'info',
    size: 'default',
    closable: false,
  },
)

defineEmits<{ (e: 'close'): void }>()

const wrapperClass = computed(() => {
  const base =
    'inline-flex items-center rounded-full border border-border bg-muted/20 px-2 py-0.5 text-xs text-foreground'
  const size = props.size === 'small' ? 'text-[11px] px-2' : props.size === 'large' ? 'text-sm px-3 py-1' : ''
  const type =
    props.type === 'success'
      ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/20'
      : props.type === 'warning'
        ? 'bg-amber-500/10 text-amber-800 border-amber-500/20'
        : props.type === 'danger'
          ? 'bg-rose-500/10 text-rose-700 border-rose-500/20'
          : props.type === 'primary'
            ? 'bg-primary/10 text-primary border-primary/20'
            : 'bg-muted/20 text-foreground border-border'

  return [base, size, type].filter(Boolean)
})
</script>
