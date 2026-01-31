<template>
  <option :value="value" :disabled="disabled">
    {{ label }}
  </option>
</template>

<script setup lang="ts">
const props = defineProps<{
  label: string
  value: any
  disabled?: boolean
}>()

// Preserve Vue's internal _value behavior when used inside <select>.
// Vue will attach _value to the option VNode.
const { label, value, disabled } = props
</script>
