import type { Directive } from 'vue'

function ensureOverlay(el: HTMLElement) {
  const existing = el.querySelector(':scope > [data-loading-overlay="true"]') as HTMLElement | null
  if (existing) return existing

  const overlay = document.createElement('div')
  overlay.dataset.loadingOverlay = 'true'
  overlay.className =
    'absolute inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm'

  const spinner = document.createElement('div')
  spinner.className = 'h-8 w-8 animate-spin rounded-full border-2 border-border border-t-primary'
  overlay.appendChild(spinner)

  const style = window.getComputedStyle(el)
  if (style.position === 'static') {
    el.style.position = 'relative'
  }
  el.appendChild(overlay)
  return overlay
}

function setLoading(el: HTMLElement, isLoading: boolean) {
  const overlay = ensureOverlay(el)
  overlay.style.display = isLoading ? '' : 'none'
  el.style.pointerEvents = isLoading ? 'none' : ''
}

export const vLoading: Directive<HTMLElement, unknown> = {
  mounted(el, binding) {
    setLoading(el, Boolean(binding.value))
  },
  updated(el, binding) {
    setLoading(el, Boolean(binding.value))
  },
  unmounted(el) {
    const overlay = el.querySelector(':scope > [data-loading-overlay="true"]') as HTMLElement | null
    overlay?.remove()
    el.style.pointerEvents = ''
  },
}
