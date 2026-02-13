<script setup lang="ts">
import { ref, computed } from 'vue'
import { Loader2, FileDown, Eye, X, ZoomIn, ZoomOut } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export interface ArtifactItem {
  name: string
  download_url: string
}

const props = defineProps<{
  open: boolean
  loading: boolean
  artifacts: ArtifactItem[]
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

// 图片预览相关
const previewVisible = ref(false)
const previewUrl = ref('')
const previewName = ref('')
const previewScale = ref(1)

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp']

function isImage(name: string): boolean {
  const lower = name.toLowerCase()
  return IMAGE_EXTENSIONS.some(ext => lower.endsWith(ext))
}

function openPreview(art: ArtifactItem) {
  previewUrl.value = art.download_url
  previewName.value = art.name
  previewScale.value = 1
  previewVisible.value = true
}

function closePreview() {
  previewVisible.value = false
  previewUrl.value = ''
  previewName.value = ''
  previewScale.value = 1
}

function zoomIn() {
  previewScale.value = Math.min(previewScale.value + 0.25, 5)
}

function zoomOut() {
  previewScale.value = Math.max(previewScale.value - 0.25, 0.25)
}

const dialogOpen = computed({
  get: () => props.open,
  set: (val: boolean) => emit('update:open', val),
})
</script>

<template>
  <Dialog v-model:open="dialogOpen">
    <DialogContent class="sm:max-w-[700px] max-h-[85vh] flex flex-col">
      <DialogHeader>
        <DialogTitle>任务产物</DialogTitle>
      </DialogHeader>
      <div class="py-2 flex-1 overflow-auto">
        <div v-if="loading" class="py-4 text-center">
          <Loader2 class="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
        </div>
        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>文件</TableHead>
              <TableHead class="w-36 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="art in artifacts" :key="art.name">
              <TableCell class="font-mono text-xs">{{ art.name }}</TableCell>
              <TableCell class="text-right">
                <div class="flex items-center justify-end gap-1">
                  <!-- 图片预览按钮 -->
                  <Button
                    v-if="isImage(art.name)"
                    variant="ghost"
                    size="xs"
                    class="h-8 px-2"
                    @click="openPreview(art)"
                  >
                    <Eye class="mr-1 h-4 w-4" />
                    预览
                  </Button>
                  <!-- 下载按钮 -->
                  <a
                    :href="art.download_url"
                    :download="isImage(art.name) ? undefined : art.name"
                    target="_blank"
                    class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 text-primary underline-offset-4 hover:underline h-8 px-2"
                  >
                    <FileDown class="mr-1 h-4 w-4" />
                    下载
                  </a>
                </div>
              </TableCell>
            </TableRow>
            <TableRow v-if="artifacts.length === 0">
              <TableCell colspan="2" class="py-4 text-center text-sm text-muted-foreground">无产物</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </DialogContent>
  </Dialog>

  <!-- 图片全屏预览遮罩 -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="previewVisible"
        class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80"
        @click.self="closePreview"
      >
        <!-- 顶部工具栏 -->
        <div class="absolute top-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-black/60 rounded-lg px-3 py-1.5 text-white text-sm">
          <span class="max-w-[300px] truncate font-mono">{{ previewName }}</span>
          <span class="text-white/60">|</span>
          <button
            class="p-1 hover:bg-white/20 rounded transition-colors"
            title="缩小"
            @click="zoomOut"
          >
            <ZoomOut class="h-4 w-4" />
          </button>
          <span class="min-w-[3rem] text-center">{{ Math.round(previewScale * 100) }}%</span>
          <button
            class="p-1 hover:bg-white/20 rounded transition-colors"
            title="放大"
            @click="zoomIn"
          >
            <ZoomIn class="h-4 w-4" />
          </button>
          <span class="text-white/60">|</span>
          <button
            class="p-1 hover:bg-white/20 rounded transition-colors"
            title="关闭"
            @click="closePreview"
          >
            <X class="h-4 w-4" />
          </button>
        </div>
        <!-- 图片 -->
        <img
          :src="previewUrl"
          :alt="previewName"
          class="max-w-[90vw] max-h-[85vh] object-contain transition-transform duration-200 select-none"
          :style="{ transform: `scale(${previewScale})` }"
          draggable="false"
        />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
