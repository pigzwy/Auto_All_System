import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

export interface BusinessZone {
  code: string
  name: string
  path: string
  icon?: string
  badge?: {
    text: string
    variant: 'hot' | 'new' | 'beta'
  }
}

// 固定的业务专区列表（后续可扩展为从 API 获取）
const BUSINESS_ZONES: BusinessZone[] = [
  {
    code: 'google-zone',
    name: 'Google 业务专区',
    path: '/google-zone',
    icon: '🚀',
    badge: { text: 'HOT', variant: 'hot' }
  },
  {
    code: 'gpt-zone',
    name: 'GPT 业务专区',
    path: '/gpt-zone',
    icon: '🤖',
    badge: { text: 'Beta', variant: 'beta' }
  }
]

export function useZoneSwitcher() {
  const router = useRouter()
  const route = useRoute()
  const zones = ref<BusinessZone[]>(BUSINESS_ZONES)
  
  // 获取当前专区
  const getCurrentZone = (): BusinessZone | undefined => {
    const currentPath = route.path
    return zones.value.find(z => currentPath.startsWith(z.path))
  }

  // 切换专区
  const switchZone = (zone: BusinessZone) => {
    router.push(zone.path)
  }

  // 跳转到专区列表
  const goToZoneList = () => {
    router.push('/zones')
  }

  // 获取其他专区（排除当前）
  const getOtherZones = (): BusinessZone[] => {
    const current = getCurrentZone()
    if (!current) return zones.value
    return zones.value.filter(z => z.code !== current.code)
  }

  return {
    zones,
    getCurrentZone,
    getOtherZones,
    switchZone,
    goToZoneList
  }
}

// 添加新专区的方法（供后续扩展使用）
export function registerZone(zone: BusinessZone) {
  const exists = BUSINESS_ZONES.find(z => z.code === zone.code)
  if (!exists) {
    BUSINESS_ZONES.push(zone)
  }
}
