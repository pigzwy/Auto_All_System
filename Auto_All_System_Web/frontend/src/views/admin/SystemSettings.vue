<template>
  <div class="space-y-6 p-5">
    <h1 class="text-2xl font-semibold text-foreground">系统设置</h1>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Card class="shadow-sm">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">基本设置</CardTitle>
        </CardHeader>
        <CardContent>
          <SimpleForm label-width="120px">
            <SimpleFormItem label="系统名称">
              <TextInput v-model="settings.systemName" />
            </SimpleFormItem>
            <SimpleFormItem label="系统Logo">
              <FileUpload>
                <Button>点击上传</Button>
              </FileUpload>
            </SimpleFormItem>
            <SimpleFormItem label="系统维护">
              <Toggle v-model="settings.maintenance" />
            </SimpleFormItem>
            <SimpleFormItem>
              <Button  variant="default" type="button">保存</Button>
            </SimpleFormItem>
          </SimpleForm>
        </CardContent>
      </Card>

      <Card class="shadow-sm">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">安全设置</CardTitle>
        </CardHeader>
        <CardContent>
          <SimpleForm label-width="120px">
            <SimpleFormItem label="密码强度">
              <SelectNative v-model="settings.passwordStrength">
                <SelectOption label="低" value="low" />
                <SelectOption label="中" value="medium" />
                <SelectOption label="高" value="high" />
              </SelectNative>
            </SimpleFormItem>
            <SimpleFormItem label="登录失败锁定">
              <Toggle v-model="settings.loginLock" />
            </SimpleFormItem>
            <SimpleFormItem label="Session超时">
              <NumberInput v-model="settings.sessionTimeout" :min="5" :max="1440" />
              <span class="ml-2 text-sm text-muted-foreground">分钟</span>
            </SimpleFormItem>
            <SimpleFormItem>
              <Button  variant="default" type="button">保存</Button>
            </SimpleFormItem>
          </SimpleForm>
        </CardContent>
      </Card>
    </div>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Card class="shadow-sm">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">支付设置</CardTitle>
        </CardHeader>
        <CardContent v-loading="paymentLoading">
          <SimpleForm label-width="120px">
            <SimpleFormItem 
              v-for="config in paymentConfigs" 
              :key="config.id" 
              :label="config.name"
            >
              <Toggle 
                v-model="config.is_enabled" 
                @change="togglePayment(config)"
              />
            </SimpleFormItem>
            <div v-if="paymentConfigs.length === 0" class="rounded-lg border border-border bg-muted/10 p-8 text-center">
              <div class="text-sm font-medium text-foreground">暂无支付方式</div>
              <div class="mt-1 text-xs text-muted-foreground">请先创建支付配置后再启用。</div>
            </div>
          </SimpleForm>
        </CardContent>
      </Card>

      <Card class="shadow-sm">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">邮件设置</CardTitle>
        </CardHeader>
        <CardContent>
          <SimpleForm label-width="120px">
            <SimpleFormItem label="SMTP服务器">
              <TextInput v-model="settings.smtpHost" />
            </SimpleFormItem>
            <SimpleFormItem label="SMTP端口">
              <NumberInput v-model="settings.smtpPort" />
            </SimpleFormItem>
            <SimpleFormItem label="发件人">
              <TextInput v-model="settings.emailFrom" />
            </SimpleFormItem>
            <SimpleFormItem>
              <Button  variant="default" type="button">保存</Button>
            </SimpleFormItem>
          </SimpleForm>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from '@/lib/element'
import { paymentsApi } from '@/api/payments'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const settings = reactive({
  systemName: 'Auto All System',
  maintenance: false,
  passwordStrength: 'medium',
  loginLock: true,
  sessionTimeout: 120,
  smtpHost: 'smtp.gmail.com',
  smtpPort: 587,
  emailFrom: 'noreply@example.com'
})

const paymentConfigs = ref<any[]>([])
const paymentLoading = ref(false)

// 加载支付配置
const loadPaymentConfigs = async () => {
  paymentLoading.value = true
  try {
    const response: any = await paymentsApi.getAllPaymentConfigs()
    console.log('支付配置响应:', response)
    // DRF返回的是数组
    paymentConfigs.value = Array.isArray(response) ? response : []
  } catch (error) {
    console.error('加载支付配置失败:', error)
    ElMessage.error('加载支付配置失败')
  } finally {
    paymentLoading.value = false
  }
}

// 切换支付方式
const togglePayment = async (config: any) => {
  const originalValue = !config.is_enabled
  try {
    await paymentsApi.patchPaymentConfig(config.id, {
      is_enabled: config.is_enabled
    })
    ElMessage.success(`${config.name} 已${config.is_enabled ? '启用' : '禁用'}`)
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error('操作失败')
    // 恢复原值
    config.is_enabled = originalValue
  }
}

onMounted(() => {
  loadPaymentConfigs()
})
</script>
