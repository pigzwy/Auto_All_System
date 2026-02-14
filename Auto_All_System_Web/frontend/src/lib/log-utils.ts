/**
 * 日志清理工具 —— 统一 Google 专区 / GPT 专区日志的格式化逻辑
 *
 * 核心职责：
 * 1. 过滤 JSON 行（与人类可读行重复）
 * 2. 清理 [celery=xxx][acc=N][email] 等冗余前缀
 * 3. 简化 ISO 时间戳为 [YYYY-MM-DD HH:MM:SS]
 */

// ── 正则 ─────────────────────────────────────────────────
// 匹配: 时间戳后所有连续的 [xxx] 方括号组 + 可选的 step/action:
const PREFIX_RE = /^(\[[^\]]*\])((?:\s*\[[^\]]*\])+)\s*(?:\S+\/\S+:\s*)?/
// 简化时间戳: [2026-02-13T11:05:19.137959+00:00] → [2026-02-13 11:05:19]
const TS_RE = /^\[(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})\.\d+[^\]]*\]/

/**
 * 清理单行日志文本
 * @param line 原始日志行
 * @returns 清理后文本，若应跳过则返回 null
 */
export function cleanLogLine(line: string): string | null {
  const text = String(line ?? '').trimEnd()
  if (!text) return null

  // 过滤 JSON 行（与人类可读行内容重复）
  if (text.trimStart().startsWith('{')) return null

  let cleaned = text

  // 只对包含 [celery= 的行清理前缀，避免误伤普通日志
  if (text.includes('[celery=')) {
    cleaned = text.replace(PREFIX_RE, '$1 ')
  }

  // 简化 ISO 时间戳
  cleaned = cleaned.replace(TS_RE, '[$1 $2]')

  return cleaned
}

/**
 * 清理多行日志文本（整段 log 字符串）
 * 用于 Task Log Dialog 展示后端 /tasks/{id}/log/ 返回的原始文本
 *
 * @param raw 原始日志文本
 * @returns 格式化后的日志文本
 */
export function cleanLogText(raw: string): string {
  if (!raw) return ''
  const lines = raw.split('\n')
  const result: string[] = []
  for (const line of lines) {
    const cleaned = cleanLogLine(line)
    if (cleaned !== null) {
      result.push(cleaned)
    }
  }
  return result.join('\n')
}

/**
 * TraceLine 类型定义
 */
export type TraceLine = {
  id: number
  text: string
  isJson: boolean
}

/**
 * 将 trace API 返回的行数组转换为清理后的 TraceLine 数组
 * 用于 Celery Trace Dialog 的实时日志展示
 *
 * @param raw 原始行数组
 * @param nextId 下一个 TraceLine 的 id（用于递增计数）
 * @returns { lines: TraceLine[], nextId: number }
 */
export function normalizeTraceLines(
  raw: string[],
  startId: number
): { lines: TraceLine[]; nextId: number } {
  const out: TraceLine[] = []
  let seq = startId
  for (const t of raw || []) {
    const cleaned = cleanLogLine(t)
    if (cleaned === null) continue
    out.push({
      id: ++seq,
      text: cleaned,
      isJson: false
    })
  }
  return { lines: out, nextId: seq }
}
