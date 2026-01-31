<template>
  <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
    <template v-if="type === 'daterange'">
      <Input
        type="date"
        :model-value="start"
        :placeholder="startPlaceholder"
        @update:modelValue="setStart"
        class="w-full sm:w-auto"
      />
      <span class="text-xs text-muted-foreground">{{ rangeSeparator }}</span>
      <Input
        type="date"
        :model-value="end"
        :placeholder="endPlaceholder"
        @update:modelValue="setEnd"
        class="w-full sm:w-auto"
      />
    </template>
    <template v-else>
      <Input
        type="date"
        :model-value="(modelValue as any) || ''"
        @update:modelValue="$emit('update:modelValue', $event)"
        class="w-full"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Input } from '@/components/ui/input'

const props = withDefaults(
  defineProps<{
    modelValue?: any
    type?: string
    startPlaceholder?: string
    endPlaceholder?: string
    rangeSeparator?: string
  }>(),
  {
    type: 'date',
    startPlaceholder: '开始日期',
    endPlaceholder: '结束日期',
    rangeSeparator: '至',
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', payload: any): void
  (e: 'change', payload: any): void
}>()

const start = computed(() => (Array.isArray(props.modelValue) ? (props.modelValue[0] ?? '') : ''))
const end = computed(() => (Array.isArray(props.modelValue) ? (props.modelValue[1] ?? '') : ''))

const setStart = (val: string | number) => {
  const next: [string, string] = [String(val ?? ''), end.value]
  emit('update:modelValue', next)
  emit('change', next)
}

const setEnd = (val: string | number) => {
  const next: [string, string] = [start.value, String(val ?? '')]
  emit('update:modelValue', next)
  emit('change', next)
}

const { modelValue, type, startPlaceholder, endPlaceholder, rangeSeparator } = props
</script>
