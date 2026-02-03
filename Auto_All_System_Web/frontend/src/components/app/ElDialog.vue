<template>
  <Dialog :open="modelValue" @update:open="onOpenChange">
    <DialogContent :style="contentStyle" class="bg-card/95 border-border/80 shadow-xl">
      <DialogHeader v-if="title">
        <DialogTitle>{{ title }}</DialogTitle>
      </DialogHeader>
      <div class="py-1">
        <slot />
      </div>
      <DialogFooter v-if="$slots.footer" class="mt-4">
        <slot name="footer" />
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title?: string
    width?: string
  }>(),
  {
    title: '',
    width: undefined,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', payload: boolean): void
}>()

const onOpenChange = (open: boolean) => {
  emit('update:modelValue', open)
}

const contentStyle = computed(() => {
  if (!props.width) return undefined
  return { maxWidth: props.width }
})

// Keep template bindings reactive.
const { modelValue, title } = toRefs(props)
</script>
