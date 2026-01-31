<template>
  <Button
    v-bind="$attrs"
    :variant="variant"
    :size="size"
    :type="nativeType"
    :disabled="disabled || loading"
    class="gap-2"
  >
    <Loading v-if="loading" class="h-4 w-4 animate-spin" />
    <component v-if="icon" :is="icon" class="h-4 w-4" />
    <slot />
  </Button>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'
import { Button } from '@/components/ui/button'
import { Loading } from '@/icons'

const props = withDefaults(
  defineProps<{
    type?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'text'
    size?: 'large' | 'default' | 'small'
    text?: boolean
    link?: boolean
    loading?: boolean
    disabled?: boolean
    icon?: Component
    nativeType?: 'button' | 'submit' | 'reset'
  }>(),
  {
    type: 'primary',
    size: 'default',
    text: false,
    link: false,
    loading: false,
    disabled: false,
    nativeType: 'button',
  },
)

const variant = computed(() => {
  if (props.link) return 'link'
  if (props.text || props.type === 'text') return 'ghost'
  if (props.type === 'danger') return 'destructive'
  if (props.type === 'warning' || props.type === 'info') return 'secondary'
  return 'default'
})

const size = computed(() => {
  if (props.size === 'large') return 'lg'
  if (props.size === 'small') return 'sm'
  return 'default'
})

const { disabled, loading, icon, nativeType } = props
</script>
