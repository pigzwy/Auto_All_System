<template>
  <div class="w-full">
    <div class="relative flex w-full items-center">
      <span v-if="$slots.prefix || prefixIcon" class="absolute left-3 text-muted-foreground">
        <slot name="prefix">
          <component :is="prefixIcon" class="h-4 w-4" />
        </slot>
      </span>

      <component
        :is="isTextarea ? Textarea : Input"
        v-model="localValue"
        v-bind="$attrs"
        :type="effectiveType"
        :class="[
          $slots.prefix || prefixIcon ? 'pl-9' : '',
          $slots.append ? 'pr-24' : '',
        ]"
        @blur="$emit('blur', $event)"
        @focus="$emit('focus', $event)"
      />

      <div v-if="$slots.append" class="absolute right-2">
        <slot name="append" />
      </div>

      <button
        v-if="showPassword && type === 'password'"
        type="button"
        class="absolute right-2 text-xs text-muted-foreground hover:text-foreground"
        @click="togglePassword"
      >
        {{ effectiveType === 'password' ? '显示' : '隐藏' }}
      </button>

      <button
        v-if="clearable && localValue"
        type="button"
        class="absolute right-2 text-xs text-muted-foreground hover:text-foreground"
        @click="clear"
      >
        清空
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

const props = withDefaults(
  defineProps<{
    modelValue?: string | number
    type?: string
    clearable?: boolean
    showPassword?: boolean
    prefixIcon?: any
  }>(),
  {
    modelValue: '',
    type: 'text',
    clearable: false,
    showPassword: false,
    prefixIcon: undefined,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', payload: string | number): void
  (e: 'change', payload: string | number): void
  (e: 'blur', payload: FocusEvent): void
  (e: 'focus', payload: FocusEvent): void
  (e: 'clear'): void
}>()

const localValue = computed({
  get: () => props.modelValue ?? '',
  set: (val) => {
    emit('update:modelValue', val)
    emit('change', val)
  },
})

const isTextarea = computed(() => props.type === 'textarea')

const effectiveType = ref(props.type)
const togglePassword = () => {
  effectiveType.value = effectiveType.value === 'password' ? 'text' : 'password'
}

const clear = () => {
  emit('update:modelValue', '')
  emit('change', '')
  emit('clear')
}

const { clearable, showPassword, prefixIcon, type } = props
</script>
