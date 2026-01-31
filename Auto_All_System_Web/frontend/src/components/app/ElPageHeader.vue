<template>
  <div class="flex items-center gap-3">
    <button type="button" class="inline-flex h-9 items-center gap-2 rounded-md border border-border px-3 text-sm hover:bg-muted" @click="$emit('back')">
      ← 返回
    </button>
    <div class="text-sm text-muted-foreground">
      <slot name="content">
        <span class="font-medium text-foreground">{{ content }}</span>
      </slot>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ content?: string }>()
defineEmits<{ (e: 'back'): void }>()
</script>
