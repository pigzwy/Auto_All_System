<template>
  <div class="flex flex-wrap items-center justify-between gap-3 text-sm">
    <div class="text-muted-foreground">共 {{ total }} 条</div>

    <div class="flex items-center gap-2">
      <select
        class="h-9 rounded-md border border-input bg-background/70 px-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        :value="pageSize"
        @change="onSizeChange"
      >
        <option v-for="s in pageSizes" :key="s" :value="s">{{ s }}/页</option>
      </select>

      <button
        type="button"
        class="h-9 rounded-md border border-border bg-background/70 px-3 transition-colors hover:bg-muted disabled:opacity-50"
        :disabled="currentPage <= 1"
        @click="setPage(currentPage - 1)"
      >
        上一页
      </button>

      <div class="min-w-[80px] text-center text-muted-foreground">
        {{ currentPage }} / {{ totalPages }}
      </div>

      <button
        type="button"
        class="h-9 rounded-md border border-border bg-background/70 px-3 transition-colors hover:bg-muted disabled:opacity-50"
        :disabled="currentPage >= totalPages"
        @click="setPage(currentPage + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    currentPage: number
    pageSize: number
    total: number
    pageSizes?: number[]
  }>(),
  {
    pageSizes: () => [10, 20, 50, 100],
  },
)

const emit = defineEmits<{
  (e: 'update:currentPage', payload: number): void
  (e: 'update:pageSize', payload: number): void
  (e: 'current-change', payload: number): void
  (e: 'size-change', payload: number): void
}>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const setPage = (page: number) => {
  const next = Math.min(totalPages.value, Math.max(1, page))
  emit('update:currentPage', next)
  emit('current-change', next)
}

const onSizeChange = (e: Event) => {
  const val = Number((e.target as HTMLSelectElement).value)
  const next = Number.isFinite(val) ? val : props.pageSize
  emit('update:pageSize', next)
  emit('size-change', next)
  // Keep page in range
  setPage(props.currentPage)
}

const { currentPage, pageSize, total, pageSizes } = props
</script>
