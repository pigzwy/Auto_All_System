<template>
  <div class="space-y-6 p-5">
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-semibold text-foreground">专区管理</h1>
        <p class="mt-1 text-sm text-muted-foreground">管理业务专区与可用状态。</p>
      </div>
      <Button variant="success" type="button" @click="showCreateDialog = true">
        <Icon><Plus /></Icon>
        添加专区
      </Button>
    </div>

    <Card class="shadow-sm">
      <CardContent class="space-y-8 p-6">
        <!-- Google业务专区 (固定卡片) -->
        <div class="space-y-4 border-b border-border pb-8">
          <h2 class="text-base font-semibold text-foreground">业务专区</h2>

          <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <button
              type="button"
              class="group relative w-full text-left rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 to-fuchsia-500/10 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-fuchsia-500/40"
              @click="openGoogleZone"
            >
              <div class="flex items-center justify-between">
                <div class="text-4xl">🚀</div>
                <Tag type="success">HOT</Tag>
              </div>

              <h3 class="mt-3 text-lg font-semibold text-foreground">Google 业务</h3>
              <p class="mt-1 text-sm text-muted-foreground">学生优惠订阅自动化</p>

              <div class="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-border bg-background/60 p-3">
                <div class="text-center">
                  <div class="text-xs text-muted-foreground">账号数</div>
                  <div class="mt-1 text-base font-semibold text-foreground">{{ googleStats.accounts }}</div>
                </div>
                <div class="text-center">
                  <div class="text-xs text-muted-foreground">已订阅</div>
                  <div class="mt-1 text-base font-semibold text-foreground">{{ googleStats.subscribed }}</div>
                </div>
              </div>

              <div class="mt-4 flex items-center justify-between">
                <span class="text-sm font-medium text-primary">自动化处理</span>
                <span class="inline-flex items-center gap-1 text-sm font-medium text-primary group-hover:underline underline-offset-4">
                  进入专区
                  <Icon><ArrowRight /></Icon>
                </span>
              </div>
            </button>
          </div>
        </div>

        <!-- 其他专区 -->
        <div v-if="zones.length > 0" class="space-y-4">
          <h2 class="text-base font-semibold text-foreground">其他专区</h2>

          <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <div
              v-for="zone in zones"
              :key="zone.id"
              class="rounded-2xl border border-border bg-background/60 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
            >
              <div class="flex items-center justify-between">
                <div class="text-4xl">{{ zone.icon || '🎯' }}</div>
                <Toggle v-model="zone.is_active" @change="toggleZone(zone)" />
              </div>

              <h3 class="mt-3 text-lg font-semibold text-foreground">{{ zone.name }}</h3>
              <p class="mt-1 text-sm text-muted-foreground">{{ zone.slug }}</p>

              <div class="mt-4 flex items-center justify-between">
                <span class="text-sm font-semibold text-emerald-600">¥{{ zone.base_price }}/次</span>
                <Button text variant="ghost" class="text-warning hover:text-warning" @click="editZone(zone)">编辑</Button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!loading && zones.length === 0" class="rounded-xl border border-border bg-muted/10 p-10 text-center">
          <div class="text-sm font-medium text-foreground">暂无其他专区</div>
          <div class="mt-1 text-xs text-muted-foreground">请先创建专区或稍后刷新。</div>
        </div>
      </CardContent>
    </Card>

    <!-- 创建/编辑对话框 -->
    <Modal v-model="showCreateDialog" title="专区配置" width="600px">
      <SimpleForm :model="zoneForm" label-width="100px">
        <SimpleFormItem label="专区名称">
          <TextInput v-model="zoneForm.name" />
        </SimpleFormItem>
        <SimpleFormItem label="专区代码">
          <TextInput v-model="zoneForm.slug" />
        </SimpleFormItem>
        <SimpleFormItem label="图标">
          <TextInput v-model="zoneForm.icon" placeholder="emoji图标" />
        </SimpleFormItem>
        <SimpleFormItem label="单价">
          <NumberInput v-model="zoneForm.base_price" :min="0" :precision="2" />
        </SimpleFormItem>
      </SimpleForm>
      <template #footer>
        <Button @click="showCreateDialog = false">取消</Button>
        <Button  variant="default" type="button" @click="handleSave">保存</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { zonesApi } from '@/api/zones'
import { googleAccountsApi } from '@/api/google'
import { ElMessage } from '@/lib/element'
import { Plus, ArrowRight } from '@/icons'
import type { Zone } from '@/types'
import { Card, CardContent } from '@/components/ui/card'

const router = useRouter()
const loading = ref(false)
const zones = ref<Zone[]>([])
const showCreateDialog = ref(false)

const googleStats = reactive({
  accounts: 0,
  subscribed: 0
})

const zoneForm = reactive({
  name: '',
  slug: '',
  icon: '',
  base_price: 0
})

const fetchZones = async () => {
  loading.value = true
  try {
    const response = await zonesApi.getZones()
    zones.value = response.results
  } catch (error) {
    ElMessage.error('获取专区列表失败')
  } finally {
    loading.value = false
  }
}

const toggleZone = (_zone: any) => {
  ElMessage.success('专区状态已更新')
}

const editZone = (_zone: any) => {
  ElMessage.info('编辑功能开发中')
}

const handleSave = () => {
  ElMessage.success('保存成功')
  showCreateDialog.value = false
}

const openGoogleZone = () => {
  router.push('/google-zone')
}

const fetchGoogleStats = async () => {
  try {
    const accountsResponse = await googleAccountsApi.getAccounts({ page_size: 1 })
    googleStats.accounts = accountsResponse.count || 0
    
    const subscribedResponse = await googleAccountsApi.getAccounts({ 
      status: 'subscribed',
      page_size: 1 
    })
    googleStats.subscribed = subscribedResponse.count || 0
  } catch (error) {
    console.error('获取Google统计数据失败:', error)
  }
}

onMounted(() => {
  fetchZones()
  fetchGoogleStats()
})
</script>
