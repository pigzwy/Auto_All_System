<template>
  <div class="w-full">
    <div class="overflow-auto rounded-xl border border-border bg-background/70 shadow-sm" :style="tableWrapperStyle">
      <table class="w-full text-sm text-foreground">
        <thead class="bg-muted/40 text-muted-foreground">
          <tr class="border-b border-border">
            <th
              v-for="col in columns"
              :key="col.id"
              class="px-3 py-2 text-left font-medium"
              :style="colStyle(col)"
            >
              <div class="flex items-center gap-2">
                <span>{{ col.label }}</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, idx) in props.data"
            :key="getRowKey(row, idx)"
            class="border-b border-border transition-colors"
            :class="[props.stripe && idx % 2 === 1 ? 'bg-muted/10' : '', 'hover:bg-muted/30']"
          >
            <td v-for="col in columns" :key="col.id" class="px-3 py-2" :style="colStyle(col)">
              <template v-if="col.type === 'selection'">
                <input
                  type="checkbox"
                  class="h-4 w-4"
                  :checked="isSelected(row, idx)"
                  @change="toggleSelection(row, idx, $event)"
                />
              </template>
              <template v-else>
                <component
                  v-if="col.slots?.default"
                  :is="SlotRenderer"
                  :slot-fn="col.slots.default"
                  :row="row"
                  :index="idx"
                />
                <span v-else class="text-foreground">
                  {{ col.prop ? (row as any)[col.prop] : '' }}
                </span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, provide, reactive, ref } from 'vue'
import type { ElTableColumnDef } from './symbols'
import { elTableKey } from './symbols'

const props = withDefaults(
  defineProps<{
    data: any[]
    stripe?: boolean
    maxHeight?: string | number
    rowKey?: string
  }>(),
  {
    data: () => [],
    stripe: false,
    maxHeight: undefined,
    rowKey: undefined,
  },
)

const emit = defineEmits<{
  (e: 'selection-change', payload: any[]): void
}>()

const columns = reactive<ElTableColumnDef[]>([])
const registerColumn = (col: ElTableColumnDef) => {
  columns.push(col)
}
const unregisterColumn = (id: string) => {
  const idx = columns.findIndex(c => c.id === id)
  if (idx >= 0) columns.splice(idx, 1)
}

provide(elTableKey, { registerColumn, unregisterColumn })

const tableWrapperStyle = computed(() => {
  if (!props.maxHeight) return undefined
  const h = typeof props.maxHeight === 'number' ? `${props.maxHeight}px` : props.maxHeight
  return { maxHeight: h }
})

const selectedKeys = ref(new Set<string>())

const getRowKey = (row: any, idx: number) => {
  if (props.rowKey && row && row[props.rowKey] != null) return String(row[props.rowKey])
  return String(idx)
}

const isSelected = (row: any, idx: number) => {
  const key = getRowKey(row, idx)
  return selectedKeys.value.has(key)
}

const toggleSelection = (row: any, idx: number, e: Event) => {
  const key = getRowKey(row, idx)
  const checked = (e.target as HTMLInputElement).checked
  if (checked) selectedKeys.value.add(key)
  else selectedKeys.value.delete(key)
  emit('selection-change', props.data.filter((r, i) => selectedKeys.value.has(getRowKey(r, i))))
}

const colStyle = (col: ElTableColumnDef) => {
  const style: Record<string, string> = {}
  if (col.width) style.width = typeof col.width === 'number' ? `${col.width}px` : String(col.width)
  if (col.minWidth) style.minWidth = typeof col.minWidth === 'number' ? `${col.minWidth}px` : String(col.minWidth)
  if (col.align === 'right') style.textAlign = 'right'
  if (col.align === 'center') style.textAlign = 'center'
  return style
}

const SlotRenderer = defineComponent({
  name: 'ElTableSlotRenderer',
  props: {
    slotFn: { type: Function, required: false },
    row: { type: Object, required: true },
    index: { type: Number, required: true },
  },
  setup(p) {
    return () => (p.slotFn as any)?.({ row: p.row, $index: p.index })
  },
})

// NOTE: do not destructure props into local variables,
// otherwise template will lose reactivity when parent updates `data`.
</script>
