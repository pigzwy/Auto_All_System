<template>
  <div class="w-full">
    <div class="grid gap-2">
      <label class="text-sm text-muted-foreground">浏览器</label>
      <div class="flex items-center gap-2">
        <Select v-model="selected" @update:modelValue="handleChange">
          <SelectTrigger class="w-full">
            <SelectValue placeholder="选择浏览器" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              v-for="browser in browsers"
              :key="browser.type"
              :value="browser.type"
              :disabled="!browser.online"
            >
              <div class="flex items-center gap-2">
                <span>{{ browser.label }}</span>
                <Badge
                  v-if="browser.online"
                  variant="outline"
                  class="rounded-full border-emerald-500/20 bg-emerald-500/10 text-emerald-700"
                >
                  在线
                </Badge>
                <Badge
                  v-else
                  variant="outline"
                  class="rounded-full border-rose-500/20 bg-rose-500/10 text-rose-700"
                >
                  离线
                </Badge>
                <Badge
                  v-if="browser.isDefault"
                  variant="outline"
                  class="rounded-full border-primary/20 bg-primary/10 text-primary"
                >
                  默认
                </Badge>
              </div>
            </SelectItem>
          </SelectContent>
        </Select>

        <Button
          v-if="selected !== defaultBrowser"
          type="button"
          variant="link"
          size="sm"
          class="h-9 px-2"
          @click="setAsDefault"
        >
          设为默认
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from '@/lib/element'
import { googleBrowserApi } from '@/api/google'

interface Browser {
  type: string
  label: string
  online: boolean
  isDefault: boolean
}

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const selected = ref(props.modelValue || 'bitbrowser')
const defaultBrowser = ref('bitbrowser')
const browsers = ref<Browser[]>([
  { type: 'bitbrowser', label: '比特浏览器', online: false, isDefault: true },
  { type: 'geekez', label: 'GeekezBrowser', online: false, isDefault: false },
])

watch(() => props.modelValue, (val) => {
  if (val) selected.value = val
})

onMounted(async () => {
  await loadBrowsers()
})

async function loadBrowsers() {
  try {
    const response = await googleBrowserApi.getAvailable()
    const data = response.data
    
    defaultBrowser.value = data.default
    
    browsers.value = data.browsers.map((b: any) => ({
      type: b.type,
      label: b.type === 'bitbrowser' ? '比特浏览器' : 'GeekezBrowser',
      online: b.online,
      isDefault: b.type === data.default,
    }))
    
    // 如果当前选择的浏览器不可用，切换到在线的浏览器
    const currentBrowser = browsers.value.find(b => b.type === selected.value)
    if (!currentBrowser?.online) {
      const onlineBrowser = browsers.value.find(b => b.online)
      if (onlineBrowser) {
        selected.value = onlineBrowser.type
        emit('update:modelValue', onlineBrowser.type)
      }
    }
  } catch (error) {
    console.error('Failed to load browsers:', error)
  }
}

function handleChange(value: string) {
  emit('update:modelValue', value)
}

async function setAsDefault() {
  try {
    await googleBrowserApi.setDefault({ browser_type: selected.value })
    defaultBrowser.value = selected.value
    browsers.value = browsers.value.map(b => ({
      ...b,
      isDefault: b.type === selected.value,
    }))
    ElMessage.success('已设置为默认浏览器')
  } catch (error) {
    ElMessage.error('设置失败')
  }
}
</script>
