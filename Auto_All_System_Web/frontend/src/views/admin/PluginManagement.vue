<template>
  <div class="space-y-6 p-5">
    <!-- 页面标题 -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-foreground">插件管理中心</h2>
        <p class="mt-1 text-sm text-muted-foreground">管理和配置系统插件，扩展系统功能</p>
      </div>
      <Button  variant="default" type="button" :icon="Refresh" @click="handleReload" :loading="reloading">
        重新加载
      </Button>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <Card class="overflow-hidden">
        <CardContent class="bg-gradient-to-br from-indigo-500 to-fuchsia-500 p-6 text-white">
          <div class="flex items-center gap-4">
            <Icon :size="40" class="opacity-90"><Box /></Icon>
            <div>
              <div class="text-3xl font-bold leading-none">{{ stats.total }}</div>
              <div class="mt-1 text-sm text-white/90">总插件数</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="overflow-hidden">
        <CardContent class="bg-gradient-to-br from-emerald-500 to-cyan-400 p-6 text-white">
          <div class="flex items-center gap-4">
            <Icon :size="40" class="opacity-90"><CircleCheck /></Icon>
            <div>
              <div class="text-3xl font-bold leading-none">{{ stats.enabled }}</div>
              <div class="mt-1 text-sm text-white/90">已启用</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="overflow-hidden">
        <CardContent class="bg-gradient-to-br from-slate-500 to-slate-400 p-6 text-white">
          <div class="flex items-center gap-4">
            <Icon :size="40" class="opacity-90"><CircleClose /></Icon>
            <div>
              <div class="text-3xl font-bold leading-none">{{ stats.disabled }}</div>
              <div class="mt-1 text-sm text-white/90">已禁用</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="overflow-hidden">
        <CardContent class="bg-gradient-to-br from-amber-500 to-orange-500 p-6 text-white">
          <div class="flex items-center gap-4">
            <Icon :size="40" class="opacity-90"><Grid /></Icon>
            <div>
              <div class="text-3xl font-bold leading-none">{{ Object.keys(stats.categories || {}).length }}</div>
              <div class="mt-1 text-sm text-white/90">插件分类</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- 筛选和搜索 -->
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardContent class="p-6">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-12">
          <div class="md:col-span-6">
            <TextInput
              v-model="searchText"
              placeholder="搜索插件名称或描述..."
              :prefix-icon="Search"
              clearable
            />
          </div>
          <div class="md:col-span-3">
            <SelectNative v-model="filterCategory" placeholder="选择分类" clearable class="w-full">
              <SelectOption label="全部分类" value="" />
              <SelectOption
                v-for="category in categories"
                :key="category"
                :label="category"
                :value="category"
              />
            </SelectNative>
          </div>
          <div class="md:col-span-3">
            <SelectNative v-model="filterStatus" placeholder="选择状态" clearable class="w-full">
              <SelectOption label="全部状态" value="" />
              <SelectOption label="已启用" value="enabled" />
              <SelectOption label="已禁用" value="disabled" />
            </SelectNative>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 插件列表 -->
    <div>
      <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card
          v-for="plugin in filteredPlugins"
          :key="plugin.name"
          class="border-2 shadow-sm transition-all hover:-translate-y-1 hover:shadow-md"
          :class="!plugin.dependencies_met ? 'border-amber-500/60' : plugin.enabled ? 'border-emerald-500/60' : 'border-border'"
        >
          <CardContent class="space-y-4 p-5">
            <div class="flex items-center justify-between border-b border-border pb-4">
              <div class="flex h-14 w-14 items-center justify-center rounded-xl bg-muted/40">
                <Icon :size="48" :class="plugin.enabled ? 'text-primary' : 'text-muted-foreground'">
                  <component :is="getIconComponent(plugin.icon)" />
                </Icon>
              </div>
              <Toggle
                v-model="plugin.enabled"
                @change="handleTogglePlugin(plugin)"
                :disabled="!plugin.dependencies_met"
                active-text="启用"
                inactive-text="禁用"
              />
            </div>

            <div>
              <h3 class="text-lg font-semibold text-foreground">{{ plugin.display_name }}</h3>
              <p class="mt-1 min-h-[40px] text-sm leading-relaxed text-muted-foreground">{{ plugin.description || '暂无描述' }}</p>

              <div class="mt-3 flex flex-wrap gap-2">
                <Tag size="small" type="info">{{ plugin.category }}</Tag>
                <Tag size="small">v{{ plugin.version }}</Tag>
                <Tag v-if="!plugin.dependencies_met" size="small" type="warning">依赖未满足</Tag>
              </div>

              <div class="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                <Icon><User /></Icon>
                <span>{{ plugin.author }}</span>
              </div>
            </div>

            <div class="flex gap-2 border-t border-border pt-4">
              <Button  variant="default" type="button" size="small" @click="handleViewDetail(plugin)" :icon="InfoFilled">
                详情
              </Button>
              <Button v-if="plugin.settings_available" size="small" @click="handleSettings(plugin)" :icon="Setting">
                配置
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <div v-if="filteredPlugins.length === 0" class="mt-8 rounded-xl border border-border bg-muted/10 p-10 text-center">
        <div class="text-sm font-medium text-foreground">没有找到符合条件的插件</div>
        <div class="mt-1 text-xs text-muted-foreground">调整筛选条件或清空搜索后重试。</div>
      </div>
    </div>

    <!-- 插件详情弹窗 -->
    <Modal
      v-model="detailDialogVisible"
      :title="currentPlugin?.display_name"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentPlugin" class="plugin-detail">
        <Descriptions :column="2" border>
          <DescriptionsItem label="插件名称">
            {{ currentPlugin.display_name }}
          </DescriptionsItem>
          <DescriptionsItem label="版本">
            <Tag>v{{ currentPlugin.version }}</Tag>
          </DescriptionsItem>
          <DescriptionsItem label="作者">
            {{ currentPlugin.author }}
          </DescriptionsItem>
          <DescriptionsItem label="分类">
            <Tag type="info">{{ currentPlugin.category }}</Tag>
          </DescriptionsItem>
          <DescriptionsItem label="状态">
            <Tag :type="currentPlugin.enabled ? 'success' : 'info'">
              {{ currentPlugin.enabled ? '已启用' : '已禁用' }}
            </Tag>
          </DescriptionsItem>
          <DescriptionsItem label="依赖">
            <Tag 
              v-if="currentPlugin.dependencies_met" 
              type="success"
            >
              已满足
            </Tag>
            <Tag v-else type="warning">未满足</Tag>
          </DescriptionsItem>
        </Descriptions>

        <div class="mt-6">
          <h4 class="text-base font-semibold text-foreground">插件描述</h4>
          <p class="mt-2 text-sm leading-relaxed text-muted-foreground">{{ currentPlugin.description || '暂无描述' }}</p>
        </div>

        <div v-if="currentPlugin.dependencies && currentPlugin.dependencies.length > 0" class="mt-6">
          <h4 class="text-base font-semibold text-foreground">依赖项</h4>
          <Tag 
            v-for="dep in currentPlugin.dependencies" 
            :key="dep"
            class="mr-2 mb-2"
          >
            {{ dep }}
          </Tag>
        </div>
      </div>

      <template #footer>
        <Button @click="detailDialogVisible = false">关闭</Button>
        <Button 
          v-if="currentPlugin?.settings_available" 
           variant="default" type="button" 
          @click="handleSettingsFromDetail"
        >
          配置插件
        </Button>
      </template>
    </Modal>

    <!-- 插件配置弹窗 -->
    <Modal
      v-model="settingsDialogVisible"
      :title="`配置 ${currentPlugin?.display_name}`"
      width="700px"
      destroy-on-close
    >
      <div v-if="pluginSettings" class="max-h-[500px] overflow-y-auto">
        <SimpleForm :model="pluginSettings" label-width="120px">
          <SimpleFormItem 
            v-for="(value, key) in pluginSettings" 
            :key="key"
            :label="formatLabel(String(key))"
          >
            <TextInput v-model="pluginSettings[key]" v-if="typeof value === 'string'" />
            <NumberInput v-model="pluginSettings[key]" v-else-if="typeof value === 'number'" />
            <Toggle v-model="pluginSettings[key]" v-else-if="typeof value === 'boolean'" />
            <TextInput 
              v-else 
              v-model="pluginSettings[key]"
              type="textarea"
              :rows="4"
            />
          </SimpleFormItem>
        </SimpleForm>
      </div>

      <template #footer>
        <Button @click="settingsDialogVisible = false">取消</Button>
        <Button 
           variant="default" type="button" 
          @click="handleSaveSettings"
          :loading="savingSettings"
        >
          保存配置
        </Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from '@/lib/element'
import {
  Refresh, Box, CircleCheck, CircleClose, Grid, Search,
  User, InfoFilled, Setting
} from '@/icons'
import pluginsApi, { type PluginInfo, type PluginStats } from '@/api/plugins'
import { Card, CardContent } from '@/components/ui/card'

// 响应式数据
const plugins = ref<PluginInfo[]>([])
const stats = ref<PluginStats>({
  total: 0,
  enabled: 0,
  disabled: 0,
  categories: {}
})

const searchText = ref('')
const filterCategory = ref('')
const filterStatus = ref('')
const loading = ref(false)
const reloading = ref(false)

const detailDialogVisible = ref(false)
const settingsDialogVisible = ref(false)
const currentPlugin = ref<PluginInfo | null>(null)
const pluginSettings = ref<any>(null)
const savingSettings = ref(false)

// 计算属性
const categories = computed(() => {
  const cats = new Set<string>()
  plugins.value.forEach(p => cats.add(p.category))
  return Array.from(cats).sort()
})

const filteredPlugins = computed(() => {
  return plugins.value.filter(plugin => {
    // 搜索过滤
    if (searchText.value) {
      const search = searchText.value.toLowerCase()
      if (
        !plugin.display_name.toLowerCase().includes(search) &&
        !plugin.description.toLowerCase().includes(search)
      ) {
        return false
      }
    }

    // 分类过滤
    if (filterCategory.value && plugin.category !== filterCategory.value) {
      return false
    }

    // 状态过滤
    if (filterStatus.value === 'enabled' && !plugin.enabled) {
      return false
    }
    if (filterStatus.value === 'disabled' && plugin.enabled) {
      return false
    }

    return true
  })
})

// 方法
const fetchPlugins = async () => {
  try {
    loading.value = true
    const response = await pluginsApi.getList()
    plugins.value = response.data || []
  } catch (error) {
    console.error('获取插件列表失败:', error)
    ElMessage.error('获取插件列表失败')
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const response = await pluginsApi.getStats()
    stats.value = response.data || stats.value
  } catch (error) {
    console.error('获取插件统计失败:', error)
  }
}

const handleTogglePlugin = async (plugin: PluginInfo) => {
  const action = plugin.enabled ? '启用' : '禁用'
  
  try {
    await ElMessageBox.confirm(
      `确定要${action}插件 "${plugin.display_name}" 吗？`,
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    if (plugin.enabled) {
      await pluginsApi.enable(plugin.name)
      ElMessage.success(`插件 "${plugin.display_name}" 已启用`)
    } else {
      await pluginsApi.disable(plugin.name)
      ElMessage.success(`插件 "${plugin.display_name}" 已禁用`)
    }

    await fetchStats()
  } catch (error: any) {
    // 恢复开关状态
    plugin.enabled = !plugin.enabled
    
    if (error !== 'cancel') {
      console.error('操作失败:', error)
      ElMessage.error(`操作失败: ${error.message || '未知错误'}`)
    }
  }
}

const handleViewDetail = async (plugin: PluginInfo) => {
  try {
    const response = await pluginsApi.getDetail(plugin.name)
    currentPlugin.value = response.data
    detailDialogVisible.value = true
  } catch (error) {
    console.error('获取插件详情失败:', error)
    ElMessage.error('获取插件详情失败')
  }
}

const handleSettings = async (plugin: PluginInfo) => {
  try {
    currentPlugin.value = plugin
    const response = await pluginsApi.getSettings(plugin.name)
    pluginSettings.value = response.data || {}
    settingsDialogVisible.value = true
  } catch (error) {
    console.error('获取插件配置失败:', error)
    ElMessage.error('获取插件配置失败')
  }
}

const handleSettingsFromDetail = () => {
  detailDialogVisible.value = false
  if (currentPlugin.value) {
    handleSettings(currentPlugin.value)
  }
}

const handleSaveSettings = async () => {
  if (!currentPlugin.value) return

  try {
    savingSettings.value = true
    await pluginsApi.updateSettings(currentPlugin.value.name, pluginSettings.value)
    ElMessage.success('插件配置已保存')
    settingsDialogVisible.value = false
  } catch (error) {
    console.error('保存插件配置失败:', error)
    ElMessage.error('保存插件配置失败')
  } finally {
    savingSettings.value = false
  }
}

const handleReload = async () => {
  try {
    await ElMessageBox.confirm(
      '重新加载将刷新所有插件，是否继续？',
      '确认操作',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    reloading.value = true
    await pluginsApi.reload()
    ElMessage.success('插件已重新加载')
    await fetchPlugins()
    await fetchStats()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('重新加载失败:', error)
      ElMessage.error('重新加载失败')
    }
  } finally {
    reloading.value = false
  }
}

const getIconComponent = (iconName: string) => {
  // 根据图标名称返回对应的图标组件
  const iconMap: Record<string, any> = {
    'el-icon-box': Box,
    'Box': Box,
    'Grid': Grid,
    'Setting': Setting,
  }
  return iconMap[iconName] || Box
}

const formatLabel = (key: string): string => {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
}

// 生命周期
onMounted(async () => {
  await fetchPlugins()
  await fetchStats()
})
</script>
