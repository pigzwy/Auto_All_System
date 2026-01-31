<template>
  <div class="grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto_1fr]">
    <div class="rounded-lg border border-border">
      <div class="border-b border-border p-2 text-sm font-medium text-foreground">待选</div>
      <div class="max-h-[320px] overflow-auto p-2">
        <label v-for="opt in availableOptions" :key="getKey(opt)" class="flex items-center gap-2 py-1 text-sm">
          <input type="checkbox" class="h-4 w-4" v-model="leftChecked" :value="getKey(opt)" />
          <span class="min-w-0 truncate">
            <slot :option="opt">
              {{ getLabel(opt) }}
            </slot>
          </span>
        </label>
      </div>
    </div>

    <div class="flex items-center justify-center gap-2 md:flex-col">
      <button type="button" class="h-9 rounded-md border border-border px-3 text-sm hover:bg-muted disabled:opacity-50" :disabled="leftChecked.length === 0" @click="moveToRight">
        &gt;
      </button>
      <button type="button" class="h-9 rounded-md border border-border px-3 text-sm hover:bg-muted disabled:opacity-50" :disabled="rightChecked.length === 0" @click="moveToLeft">
        &lt;
      </button>
    </div>

    <div class="rounded-lg border border-border">
      <div class="border-b border-border p-2 text-sm font-medium text-foreground">已选</div>
      <div class="max-h-[320px] overflow-auto p-2">
        <label v-for="opt in selectedOptions" :key="getKey(opt)" class="flex items-center gap-2 py-1 text-sm">
          <input type="checkbox" class="h-4 w-4" v-model="rightChecked" :value="getKey(opt)" />
          <span class="min-w-0 truncate">
            <slot :option="opt">
              {{ getLabel(opt) }}
            </slot>
          </span>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: Array<string | number>
    data: any[]
    props?: { key?: string; label?: string; disabled?: string }
  }>(),
  {
    data: () => [],
    props: () => ({ key: 'key', label: 'label', disabled: 'disabled' }),
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', payload: Array<string | number>): void
}>()

const getKey = (opt: any) => opt?.[props.props.key ?? 'key']
const getLabel = (opt: any) => opt?.[props.props.label ?? 'label']

const selectedSet = computed(() => new Set(props.modelValue))
const selectedOptions = computed(() => props.data.filter(o => selectedSet.value.has(getKey(o))))
const availableOptions = computed(() => props.data.filter(o => !selectedSet.value.has(getKey(o))))

const leftChecked = ref<Array<string | number>>([])
const rightChecked = ref<Array<string | number>>([])

const moveToRight = () => {
  const next = Array.from(new Set([...props.modelValue, ...leftChecked.value]))
  emit('update:modelValue', next)
  leftChecked.value = []
}

const moveToLeft = () => {
  const remove = new Set(rightChecked.value)
  const next = props.modelValue.filter(k => !remove.has(k))
  emit('update:modelValue', next)
  rightChecked.value = []
}

// props used via computed and emit
</script>
