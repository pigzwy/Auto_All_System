<template>
  <div class="relative my-6 flex items-center">
    <div class="flex-grow border-t border-border" />
    <span v-if="$slots.default" class="mx-3 text-xs text-muted-foreground">
      <slot />
    </span>
    <div class="flex-grow border-t border-border" />
  </div>
</template>

<script setup lang="ts">
</script>
