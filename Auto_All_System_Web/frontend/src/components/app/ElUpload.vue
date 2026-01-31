<template>
  <label class="inline-flex">
    <input
      type="file"
      class="hidden"
      :accept="accept"
      @change="onChange"
    />
    <slot />
  </label>
</template>

<script setup lang="ts">
const props = defineProps<{
  accept?: string
  beforeUpload?: (file: File) => boolean | Promise<boolean>
  showFileList?: boolean
  action?: string
}>()

const emit = defineEmits<{ (e: 'change', file: File): void }>()

const onChange = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  emit('change', file)
  const ok = props.beforeUpload ? await props.beforeUpload(file) : true
  if (!ok) {
    input.value = ''
    return
  }

  // This compat component intentionally does not auto-upload.
  input.value = ''
}

const { accept } = props
</script>
