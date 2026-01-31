<template>
  <button
    type="button"
    class="h-9 rounded-md border border-border px-3 text-sm transition-colors"
    :class="isActive ? 'bg-primary text-primary-foreground border-primary' : 'bg-background hover:bg-muted'"
    @click="select"
  >
    <slot />
  </button>
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
