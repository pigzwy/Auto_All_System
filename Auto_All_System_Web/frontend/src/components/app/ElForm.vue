<template>
  <form class="w-full" @submit.prevent>
    <div :class="inline ? 'flex flex-wrap items-end gap-4' : 'space-y-5'">
      <slot />
    </div>
  </form>
</template>

<script setup lang="ts">
import { provide, reactive } from 'vue'
import type { ElFormItemCtx, ElFormRules } from './symbols'
import { elFormKey } from './symbols'

const props = withDefaults(
  defineProps<{
    model: Record<string, unknown>
    rules?: ElFormRules
    inline?: boolean
    labelPosition?: 'top' | 'left' | 'right'
    labelWidth?: string
  }>(),
  {
    rules: undefined,
    inline: false,
    labelPosition: 'top',
    labelWidth: undefined,
  },
)

const items = reactive(new Set<ElFormItemCtx>())

const registerItem = (item: ElFormItemCtx) => {
  items.add(item)
}

const unregisterItem = (item: ElFormItemCtx) => {
  items.delete(item)
}

const isEmpty = (value: unknown) => {
  if (value === null || value === undefined) return true
  if (typeof value === 'string') return value.trim().length === 0
  if (Array.isArray(value)) return value.length === 0
  return false
}

const validate = async (cb?: (valid: boolean) => void | Promise<void>) => {
  let valid = true
  for (const item of items) {
    item.clearError()
    if (!item.prop) continue

    const rules = props.rules?.[item.prop] ?? []
    const value = props.model[item.prop]
    for (const rule of rules) {
      if (rule.required && isEmpty(value)) {
        item.setError(rule.message || '必填项')
        valid = false
        break
      }

      if (typeof rule.min === 'number' && typeof value === 'string' && value.length < rule.min) {
        item.setError(rule.message || `最少 ${rule.min} 位`)
        valid = false
        break
      }

      if (typeof rule.max === 'number' && typeof value === 'string' && value.length > rule.max) {
        item.setError(rule.message || `最多 ${rule.max} 位`)
        valid = false
        break
      }

      if (rule.pattern && typeof value === 'string' && !rule.pattern.test(value)) {
        item.setError(rule.message || '格式不正确')
        valid = false
        break
      }

      if (rule.type === 'email' && typeof value === 'string' && value.trim().length > 0) {
        // Simple email validation (close enough for UI validation)
        const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRe.test(value)) {
          item.setError(rule.message || '请输入正确的邮箱')
          valid = false
          break
        }
      }

      if (rule.validator) {
        let errMsg = ''
        const callback = (err?: Error) => {
          if (err) errMsg = err.message || rule.message || '校验失败'
        }

        try {
          await rule.validator(rule, value, callback)
        } catch (e: any) {
          errMsg = e?.message || rule.message || '校验失败'
        }

        if (errMsg) {
          item.setError(errMsg)
          valid = false
          break
        }
      }
    }
  }

  if (cb) await cb(valid)
  return valid
}

const resetFields = () => {
  for (const item of items) item.clearError()
}

provide(elFormKey, {
  model: props.model,
  rules: props.rules,
  inline: props.inline,
  labelPosition: props.labelPosition,
  labelWidth: props.labelWidth,
  registerItem,
  unregisterItem,
})

defineExpose({
  validate,
  resetFields,
})

const { inline } = props
</script>
