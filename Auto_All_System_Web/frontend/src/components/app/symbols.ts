import type { InjectionKey, Slot } from 'vue'

export type ElFormRule = {
  required?: boolean
  message?: string
  min?: number
  max?: number
  pattern?: RegExp

  // Element Plus compatible fields (ignored or partially supported)
  trigger?: string
  type?: string
  validator?: (rule: unknown, value: unknown, callback: (err?: Error) => void) => void | Promise<void>
}

export type ElFormRules = Record<string, ElFormRule[]>

export type ElFormItemCtx = {
  prop?: string
  setError: (msg: string) => void
  clearError: () => void
}

export type ElFormCtx = {
  model: Record<string, unknown>
  rules?: ElFormRules
  inline: boolean
  labelPosition: 'top' | 'left' | 'right'
  labelWidth?: string
  registerItem: (item: ElFormItemCtx) => void
  unregisterItem: (item: ElFormItemCtx) => void
}

export const elFormKey: InjectionKey<ElFormCtx> = Symbol('el-form')

export type ElTableColumnDef = {
  id: string
  type?: string
  prop?: string
  label?: string
  width?: string | number
  minWidth?: string | number
  align?: 'left' | 'center' | 'right'
  sortable?: boolean | 'custom'
  slots?: {
    default?: Slot
  }
}

export type ElTableCtx = {
  registerColumn: (col: ElTableColumnDef) => void
  unregisterColumn: (id: string) => void
}

export const elTableKey: InjectionKey<ElTableCtx> = Symbol('el-table')
