<template>
  <div v-if="false" />
</template>

<script setup lang="ts">
import { inject, onBeforeUnmount, onMounted, useSlots } from 'vue'
import { elTableKey } from './symbols'

const props = defineProps<{
  type?: string
  prop?: string
  label?: string
  width?: string | number
  minWidth?: string | number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean | 'custom'
}>()

const table = inject(elTableKey, null)
const slots = useSlots()

const id = `col_${Math.random().toString(36).slice(2)}`

onMounted(() => {
  table?.registerColumn({
    id,
    type: props.type,
    prop: props.prop,
    label: props.label,
    width: props.width,
    minWidth: props.minWidth,
    align: props.align,
    sortable: props.sortable,
    slots: {
      default: slots.default,
    },
  })
})

onBeforeUnmount(() => {
  table?.unregisterColumn(id)
})
</script>
