import { reactive } from 'vue'
import { toast } from '@/components/ui/toast'

// ─── ElMessage ───────────────────────────────────────────────
// 兼容 element-plus 的 ElMessage API，底层走 shadcn toast

type MessageType = 'success' | 'error' | 'warning' | 'info'

interface MessageOptions {
  message?: string
  type?: MessageType
  duration?: number
  [key: string]: unknown
}

function showMessage(msgOrOpts: string | MessageOptions, type: MessageType = 'info') {
  const message = typeof msgOrOpts === 'string' ? msgOrOpts : (msgOrOpts.message ?? '')
  const variant = type === 'error' ? 'destructive' as const : 'default' as const

  const titleMap: Record<MessageType, string> = {
    success: '成功',
    error: '错误',
    warning: '警告',
    info: '提示',
  }

  toast({
    title: titleMap[type],
    description: message,
    variant,
  })
}

export const ElMessage = {
  success: (msg: string | MessageOptions) => showMessage(msg, 'success'),
  error: (msg: string | MessageOptions) => showMessage(msg, 'error'),
  warning: (msg: string | MessageOptions) => showMessage(msg, 'warning'),
  info: (msg: string | MessageOptions) => showMessage(msg, 'info'),
}

// ─── ElMessageBox ────────────────────────────────────────────
// 兼容 element-plus 的 ElMessageBox API，底层走 MessageBoxHost (shadcn Dialog)

type MessageBoxKind = 'alert' | 'confirm' | 'prompt'

interface MessageBoxOptions {
  title?: string
  type?: string
  confirmButtonText?: string
  cancelButtonText?: string
  dangerouslyUseHTMLString?: boolean
  inputPlaceholder?: string
  inputPattern?: RegExp
  inputErrorMessage?: string
  inputValue?: string
  showCancelButton?: boolean
  [key: string]: unknown
}

interface MessageBoxState {
  open: boolean
  kind: MessageBoxKind
  title: string
  message: string
  type: string
  confirmText: string
  cancelText: string
  dangerouslyUseHTMLString: boolean
  showCancel: boolean
  inputValue: string
  inputPlaceholder: string
  inputPattern?: RegExp
  inputErrorMessage: string
}

let _resolve: ((value: { value: string } | void) => void) | null = null
let _reject: ((reason: string) => void) | null = null

export const messageBoxState = reactive<MessageBoxState>({
  open: false,
  kind: 'alert',
  title: '',
  message: '',
  type: '',
  confirmText: '确定',
  cancelText: '取消',
  dangerouslyUseHTMLString: false,
  showCancel: false,
  inputValue: '',
  inputPlaceholder: '',
  inputPattern: undefined,
  inputErrorMessage: '',
})

function openMessageBox(
  message: string,
  titleOrOpts?: string | MessageBoxOptions,
  opts?: MessageBoxOptions,
  kind: MessageBoxKind = 'alert',
): Promise<{ value: string } | void> {
  const title = typeof titleOrOpts === 'string' ? titleOrOpts : '提示'
  const options: MessageBoxOptions = typeof titleOrOpts === 'object' ? titleOrOpts : (opts ?? {})

  messageBoxState.open = true
  messageBoxState.kind = kind
  messageBoxState.title = title
  messageBoxState.message = message
  messageBoxState.type = (options.type as string) ?? ''
  messageBoxState.confirmText = options.confirmButtonText ?? '确定'
  messageBoxState.cancelText = options.cancelButtonText ?? '取消'
  messageBoxState.dangerouslyUseHTMLString = options.dangerouslyUseHTMLString ?? false
  messageBoxState.showCancel = kind !== 'alert'
  messageBoxState.inputValue = options.inputValue ?? ''
  messageBoxState.inputPlaceholder = options.inputPlaceholder ?? ''
  messageBoxState.inputPattern = options.inputPattern
  messageBoxState.inputErrorMessage = options.inputErrorMessage ?? ''

  return new Promise((resolve, reject) => {
    _resolve = resolve
    _reject = reject
  })
}

function confirmBox() {
  const kind = messageBoxState.kind

  if (kind === 'prompt') {
    const { inputPattern, inputErrorMessage, inputValue } = messageBoxState
    if (inputPattern && !inputPattern.test(inputValue)) {
      // 校验不通过时不关闭
      return
    }
    _resolve?.({ value: inputValue })
  } else {
    _resolve?.()
  }

  messageBoxState.open = false
  _resolve = null
  _reject = null
}

function cancelBox() {
  messageBoxState.open = false
  _reject?.('cancel')
  _resolve = null
  _reject = null
}

export const ElMessageBox = {
  alert: (message: string, title?: string | MessageBoxOptions, opts?: MessageBoxOptions) =>
    openMessageBox(message, title, opts, 'alert'),
  confirm: (message: string, title?: string | MessageBoxOptions, opts?: MessageBoxOptions) =>
    openMessageBox(message, title, opts, 'confirm'),
  prompt: (message: string, title?: string | MessageBoxOptions, opts?: MessageBoxOptions) =>
    openMessageBox(message, title, opts, 'prompt'),
}

// ─── useMessageBoxState ──────────────────────────────────────
// 供 MessageBoxHost.vue 消费

export function useMessageBoxState() {
  return {
    state: messageBoxState,
    confirm: confirmBox,
    cancel: cancelBox,
  }
}
