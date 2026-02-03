<template>
  <div class="space-y-6 p-5">
    <Card class="shadow-sm border-border/80 bg-background/80">
      <CardHeader>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle class="text-base">GeekezBrowser 配置</CardTitle>
            <p class="mt-1 text-xs text-muted-foreground">默认本机：Control 19527 / API 12138</p>
          </div>
          <div class="flex flex-wrap justify-end gap-2">
            <Button @click="load" :loading="loading">刷新</Button>
            <Button @click="applyLocalPreset">本机直连</Button>
            <Button @click="applyDockerPreset">Docker 推荐</Button>
            <Button @click="test" :loading="testing">测试连接</Button>
            <Button  variant="default" type="button" @click="save" :loading="saving">保存</Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <SimpleForm :model="form" label-width="160px">
        <Divider content-position="left">Control Server（用于 launch/wsEndpoint）</Divider>

        <SimpleFormItem label="Control Host">
          <TextInput v-model="form.control_host" placeholder="127.0.0.1" />
        </SimpleFormItem>
        <SimpleFormItem label="Control Port">
          <NumberInput v-model="form.control_port" :min="1" :max="65535" />
          <div class="mt-2 text-xs text-muted-foreground">默认 19527（Control Server），不要填 12138（那是 API Server）。Docker 场景下如果 Geekez 仅监听 127.0.0.1，可用转发端口 19528。</div>
        </SimpleFormItem>

        <SimpleFormItem label="Control Token">
          <TextInput
            v-model="form.control_token"
            show-password
            placeholder="可选；留空表示不修改"
          />
          <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            当前已保存 token：
            <Tag size="small" :type="form.has_control_token ? 'success' : 'info'">
              {{ form.has_control_token ? 'YES' : 'NO' }}
            </Tag>
            <Button v-if="form.has_control_token" text  variant="destructive" type="button" @click="clearToken">
              清空
            </Button>
          </div>
        </SimpleFormItem>

        <Divider content-position="left">API Server（用于 stop 回收环境）</Divider>

        <SimpleFormItem label="API Host">
          <TextInput v-model="form.api_server_host" placeholder="127.0.0.1" />
          <div class="mt-2 text-xs text-muted-foreground">官方文档默认只监听 127.0.0.1；Docker 场景需要使用可达地址（例如 host.docker.internal），并配合转发端口。</div>
        </SimpleFormItem>
        <SimpleFormItem label="API Port">
          <NumberInput v-model="form.api_server_port" :min="1" :max="65535" />
          <div class="mt-2 text-xs text-muted-foreground">默认 12138（API Server）。Docker 场景如果 Geekez 只监听 127.0.0.1，可用转发端口 12139。</div>
        </SimpleFormItem>
      </SimpleForm>
      </CardContent>
    </Card>

    <Card v-if="testResult" class="shadow-sm">
      <CardHeader class="pb-3">
        <CardTitle class="text-base">连接测试结果</CardTitle>
      </CardHeader>

      <CardContent>
        <Descriptions :column="1" border>
        <DescriptionsItem label="Control Server">
          <Tag :type="testResult.control.ok ? 'success' : 'danger'">
            {{ testResult.control.ok ? 'OK' : 'FAIL' }}
          </Tag>
          <span class="ml-2 font-mono text-xs text-muted-foreground">{{ testResult.control.base_url }}</span>
          <span class="ml-2 font-mono text-xs text-muted-foreground">{{ testResult.control.latency_ms }}ms</span>
          <span v-if="testResult.control.note" class="ml-2 text-xs text-primary">{{ testResult.control.note }}</span>
          <span v-if="testResult.control.error" class="ml-2 text-xs text-rose-600">{{ testResult.control.error }}</span>

          <Collapse v-if="(testResult.control.attempts || []).length" class="mt-3">
            <CollapseItem title="查看探测明细" name="control">
              <DataTable :data="testResult.control.attempts" size="small" class="w-full">
                <DataColumn prop="url" label="URL" min-width="260" />
                <DataColumn prop="ok" label="OK" width="70">
                  <template #default="scope">
                    <Tag size="small" :type="scope.row.ok ? 'success' : 'danger'">
                      {{ scope.row.ok ? 'YES' : 'NO' }}
                    </Tag>
                  </template>
                </DataColumn>
                <DataColumn prop="status_code" label="HTTP" width="80" />
                <DataColumn prop="error" label="Error" min-width="260" />
              </DataTable>
            </CollapseItem>
          </Collapse>
        </DescriptionsItem>
        <DescriptionsItem label="API Server">
          <Tag :type="testResult.api_server.ok ? 'success' : 'danger'">
            {{ testResult.api_server.ok ? 'OK' : 'FAIL' }}
          </Tag>
          <span class="ml-2 font-mono text-xs text-muted-foreground">{{ testResult.api_server.url }}</span>
          <span class="ml-2 font-mono text-xs text-muted-foreground">{{ testResult.api_server.latency_ms }}ms</span>
          <span v-if="testResult.api_server.status_code" class="ml-2 font-mono text-xs text-muted-foreground">HTTP {{ testResult.api_server.status_code }}</span>
          <span v-if="testResult.api_server.note" class="ml-2 text-xs text-primary">{{ testResult.api_server.note }}</span>
          <span v-if="testResult.api_server.error" class="ml-2 text-xs text-rose-600">{{ testResult.api_server.error }}</span>

          <Collapse v-if="(testResult.api_server.attempts || []).length" class="mt-3">
            <CollapseItem title="查看探测明细" name="api">
              <DataTable :data="testResult.api_server.attempts" size="small" class="w-full">
                <DataColumn prop="url" label="URL" min-width="260" />
                <DataColumn prop="ok" label="OK" width="70">
                  <template #default="scope">
                    <Tag size="small" :type="scope.row.ok ? 'success' : 'danger'">
                      {{ scope.row.ok ? 'YES' : 'NO' }}
                    </Tag>
                  </template>
                </DataColumn>
                <DataColumn prop="status_code" label="HTTP" width="80" />
                <DataColumn prop="error" label="Error" min-width="260" />
              </DataTable>
            </CollapseItem>
          </Collapse>
        </DescriptionsItem>
      </Descriptions>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from '@/lib/element'
import { geekezApi, type GeekezConnectionTestResult } from '@/api/geekez'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<GeekezConnectionTestResult | null>(null)

const form = reactive({
  control_host: '127.0.0.1',
  control_port: 19527,
  api_server_host: '127.0.0.1',
  api_server_port: 12138,
  has_control_token: false,
  control_token: ''
})

const load = async () => {
  loading.value = true
  try {
    const cfg = await geekezApi.getConfig()
    form.control_host = cfg.control_host || '127.0.0.1'
    form.control_port = cfg.control_port || 19527
    form.api_server_host = cfg.api_server_host || '127.0.0.1'
    form.api_server_port = cfg.api_server_port || 12138
    form.has_control_token = !!cfg.has_control_token
    form.control_token = ''
  } catch (e: any) {
    ElMessage.error(e?.message || '加载配置失败')
  } finally {
    loading.value = false
  }
}

const buildPayload = (opts?: { includeToken?: boolean; clearToken?: boolean }) => {
  const payload: any = {
    control_host: form.control_host,
    control_port: form.control_port,
    api_server_host: form.api_server_host,
    api_server_port: form.api_server_port
  }

  if (opts?.clearToken) {
    payload.control_token = ''
  } else if (opts?.includeToken && form.control_token.trim()) {
    payload.control_token = form.control_token.trim()
  }

  return payload
}

const save = async () => {
  saving.value = true
  try {
    const payload = buildPayload({ includeToken: true })
    await geekezApi.updateConfig(payload)
    ElMessage.success('保存成功')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const test = async () => {
  testing.value = true
  try {
    const payload = buildPayload({ includeToken: true })
    testResult.value = await geekezApi.testConnection(payload)
    ElMessage.success('测试完成')
  } catch (e: any) {
    ElMessage.error(e?.message || '测试失败')
  } finally {
    testing.value = false
  }
}

const clearToken = async () => {
  saving.value = true
  try {
    await geekezApi.updateConfig(buildPayload({ clearToken: true }))
    ElMessage.success('已清空')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.message || '清空失败')
  } finally {
    saving.value = false
  }
}

const applyLocalPreset = () => {
  form.control_host = '127.0.0.1'
  form.control_port = 19527
  form.api_server_host = '127.0.0.1'
  form.api_server_port = 12138
}

const applyDockerPreset = () => {
  // Linux Docker: host-local-only service needs forwarding
  form.control_host = 'host.docker.internal'
  form.control_port = 19528
  form.api_server_host = 'host.docker.internal'
  form.api_server_port = 12139
}

onMounted(() => {
  load()
})
</script>
