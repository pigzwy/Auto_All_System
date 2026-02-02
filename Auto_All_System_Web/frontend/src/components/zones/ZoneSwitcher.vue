<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" size="sm" class="gap-2 px-2 hover:bg-muted">
        <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-lg">
          {{ currentZone?.icon || '📁' }}
        </div>
        <h1 class="text-base font-semibold">{{ currentZone?.name || '未知专区' }}</h1>
        <Badge
          v-if="currentZone?.badge"
          variant="outline"
          :class="badgeClass"
        >
          {{ currentZone.badge.text }}
        </Badge>
        <ChevronDown class="h-4 w-4 text-muted-foreground" />
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="start" class="w-56">
      <DropdownMenuItem
        v-for="zone in zones"
        :key="zone.code"
        class="gap-2"
        :class="{ 'bg-accent': zone.code === currentZone?.code }"
        @select="zone.code !== currentZone?.code && switchZone(zone)"
      >
        <span class="text-base">{{ zone.icon }}</span>
        <span>{{ zone.name }}</span>
        <Badge
          v-if="zone.badge"
          variant="outline"
          class="ml-auto text-xs"
          :class="getBadgeClass(zone.badge.variant)"
        >
          {{ zone.badge.text }}
        </Badge>
      </DropdownMenuItem>
      <DropdownMenuSeparator />
      <DropdownMenuItem class="gap-2" @select="goToZoneList">
        <LayoutGrid class="h-4 w-4" />
        <span>查看所有专区</span>
      </DropdownMenuItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronDown, LayoutGrid } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useZoneSwitcher } from '@/composables/useZoneSwitcher'

const { zones, getCurrentZone, switchZone, goToZoneList } = useZoneSwitcher()

const currentZone = computed(() => getCurrentZone())

const badgeClass = computed(() => {
  if (!currentZone.value?.badge) return ''
  return getBadgeClass(currentZone.value.badge.variant)
})

function getBadgeClass(variant: string) {
  switch (variant) {
    case 'hot':
      return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
    case 'new':
      return 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
    case 'beta':
      return 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
    default:
      return ''
  }
}
</script>
