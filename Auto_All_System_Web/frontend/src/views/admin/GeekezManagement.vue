<template>
  <div class="geekez-management">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <div class="title">GeekezBrowser 配置</div>
            <div class="sub">默认本机：Control 19527 / API 12138</div>
          </div>
          <div class="actions">
            <el-button @click="load" :loading="loading">刷新</el-button>
            <el-button @click="applyLocalPreset">本机直连</el-button>
            <el-button @click="applyDockerPreset">Docker 推荐</el-button>
            <el-button @click="test" :loading="testing">测试连接</el-button>
            <el-button type="primary" @click="save" :loading="saving">保存</el-button>
          </div>
        </div>
      </template>

      <el-form :model="form" label-width="160px">
        <el-divider content-position="left">Control Server（用于 launch/wsEndpoint）</el-divider>

        <el-form-item label="Control Host">
          <el-input v-model="form.control_host" placeholder="127.0.0.1" />
        </el-form-item>
        <el-form-item label="Control Port">
          <el-input-number v-model="form.control_port" :min="1" :max="65535" />
          <div class="hint">默认 19527（Control Server），不要填 12138（那是 API Server）。Docker 场景下如果 Geekez 仅监听 127.0.0.1，可用转发端口 19528。</div>
        </el-form-item>

        <el-form-item label="Control Token">
          <el-input
            v-model="form.control_token"
            show-password
            placeholder="可选；留空表示不修改"
          />
          <div class="hint">
            当前已保存 token：
            <el-tag size="small" :type="form.has_control_token ? 'success' : 'info'">
              {{ form.has_control_token ? 'YES' : 'NO' }}
            </el-tag>
            <el-button v-if="form.has_control_token" text type="danger" @click="clearToken">
              清空
            </el-button>
          </div>
        </el-form-item>

        <el-divider content-position="left">API Server（用于 stop 回收环境）</el-divider>

        <el-form-item label="API Host">
          <el-input v-model="form.api_server_host" placeholder="127.0.0.1" />
          <div class="hint">官方文档默认只监听 127.0.0.1；Docker 场景需要使用可达地址（例如 host.docker.internal），并配合转发端口。</div>
        </el-form-item>
        <el-form-item label="API Port">
          <el-input-number v-model="form.api_server_port" :min="1" :max="65535" />
          <div class="hint">默认 12138（API Server）。Docker 场景如果 Geekez 只监听 127.0.0.1，可用转发端口 12139。</div>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="testResult" shadow="never" style="margin-top: 16px;">
      <template #header>
        <div class="card-header">
          <div class="title">连接测试结果</div>
        </div>
      </template>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="Control Server">
          <el-tag :type="testResult.control.ok ? 'success' : 'danger'">
            {{ testResult.control.ok ? 'OK' : 'FAIL' }}
          </el-tag>
          <span class="mono">{{ testResult.control.base_url }}</span>
          <span class="mono">{{ testResult.control.latency_ms }}ms</span>
          <span v-if="testResult.control.note" class="note">{{ testResult.control.note }}</span>
          <span v-if="testResult.control.error" class="error">{{ testResult.control.error }}</span>

          <el-collapse v-if="(testResult.control.attempts || []).length" class="collapse">
            <el-collapse-item title="查看探测明细" name="control">
              <el-table :data="testResult.control.attempts" size="small" style="width: 100%">
                <el-table-column prop="url" label="URL" min-width="260" />
                <el-table-column prop="ok" label="OK" width="70">
                  <template #default="scope">
                    <el-tag size="small" :type="scope.row.ok ? 'success' : 'danger'">
                      {{ scope.row.ok ? 'YES' : 'NO' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status_code" label="HTTP" width="80" />
                <el-table-column prop="error" label="Error" min-width="260" />
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </el-descriptions-item>
        <el-descriptions-item label="API Server">
          <el-tag :type="testResult.api_server.ok ? 'success' : 'danger'">
            {{ testResult.api_server.ok ? 'OK' : 'FAIL' }}
          </el-tag>
          <span class="mono">{{ testResult.api_server.url }}</span>
          <span class="mono">{{ testResult.api_server.latency_ms }}ms</span>
          <span v-if="testResult.api_server.status_code" class="mono">HTTP {{ testResult.api_server.status_code }}</span>
          <span v-if="testResult.api_server.note" class="note">{{ testResult.api_server.note }}</span>
          <span v-if="testResult.api_server.error" class="error">{{ testResult.api_server.error }}</span>

          <el-collapse v-if="(testResult.api_server.attempts || []).length" class="collapse">
            <el-collapse-item title="查看探测明细" name="api">
              <el-table :data="testResult.api_server.attempts" size="small" style="width: 100%">
                <el-table-column prop="url" label="URL" min-width="260" />
                <el-table-column prop="ok" label="OK" width="70">
                  <template #default="scope">
                    <el-tag size="small" :type="scope.row.ok ? 'success' : 'danger'">
                      {{ scope.row.ok ? 'YES' : 'NO' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status_code" label="HTTP" width="80" />
                <el-table-column prop="error" label="Error" min-width="260" />
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { geekezApi, type GeekezConnectionTestResult } from '@/api/geekez'

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

<style scoped lang="scss">
.geekez-management {
  .card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;

    .title {
      font-weight: 700;
      color: #111827;
    }

    .sub {
      font-size: 12px;
      color: #6b7280;
      margin-top: 4px;
    }
  }

  .actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .hint {
    font-size: 12px;
    color: #6b7280;
    margin-top: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    margin-left: 8px;
    color: #374151;
  }

  .error {
    margin-left: 8px;
    color: #dc2626;
    font-size: 12px;
  }

  .note {
    margin-left: 8px;
    color: #2563eb;
    font-size: 12px;
  }

  .collapse {
    margin-top: 10px;
  }
}
</style>
