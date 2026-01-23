<template>
  <div class="browser-selector">
    <el-form-item label="浏览器">
      <el-select v-model="selected" placeholder="选择浏览器" @change="handleChange">
        <el-option
          v-for="browser in browsers"
          :key="browser.type"
          :label="browser.label"
          :value="browser.type"
          :disabled="!browser.online"
        >
          <div class="browser-option">
            <span>{{ browser.label }}</span>
            <el-tag v-if="browser.online" type="success" size="small">在线</el-tag>
            <el-tag v-else type="danger" size="small">离线</el-tag>
            <el-tag v-if="browser.isDefault" type="primary" size="small">默认</el-tag>
          </div>
        </el-option>
      </el-select>
      <el-button 
        v-if="selected !== defaultBrowser" 
        type="text" 
        size="small" 
        @click="setAsDefault"
        class="set-default-btn"
      >
        设为默认
      </el-button>
    </el-form-item>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
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

<style scoped lang="scss">
.browser-selector {
  .browser-option {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .set-default-btn {
    margin-left: 8px;
  }
}
</style>
