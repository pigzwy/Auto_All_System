/**
 * GPT 业务专区路由配置（预留）
 *
 * 说明：当前项目的主路由在 `src/router/index.ts` 里直接维护。
 * 这里保留模块化定义，便于后续接入侧边栏/动态菜单。
 */
import type { RouteRecordRaw } from 'vue-router'

export const gptRoutes: Array<RouteRecordRaw> = [
  {
    path: '/gpt-zone',
    name: 'GptBusinessZone',
    component: () => import('@/views/zones/GptBusinessZone.vue'),
    meta: {
      title: 'GPT 业务',
      requiresAuth: true
    }
  }
]
