<template>
  <div class="google-accounts-module">
    <div class="module-header">
      <div class="left-panel">
        <h2>谷歌账号管理</h2>
      </div>
      <div class="right-panel">
        <el-button-group>
          <el-button type="primary" @click="showDialog = true">
            <el-icon><Plus /></el-icon>
            添加账号
          </el-button>
          <el-button type="success" @click="showImportDialog = true">
            <el-icon><Upload /></el-icon>
            批量导入
          </el-button>
          <el-dropdown class="ml-2" trigger="click" @command="handleExportCommand">
             <el-button type="primary" plain>
               <el-icon class="mr-1"><Download /></el-icon> 导出 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
             </el-button>
             <template #dropdown>
               <el-dropdown-menu>
                 <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
                 <el-dropdown-item command="txt">导出 TXT</el-dropdown-item>
               </el-dropdown-menu>
             </template>
          </el-dropdown>
        </el-button-group>
      </div>
    </div>

    <!-- 筛选和批量操作栏 -->
    <el-card shadow="never" class="mb-4 operation-panel">
      <div class="flex-row">
        <div class="filters">
          <el-select v-model="filterType" placeholder="账号状态筛选" clearable @change="fetchAccounts" style="width: 160px">
            <el-option label="全部" value="" />
            <el-option label="无资格" value="ineligible" />
            <el-option label="未绑卡" value="unbound_card" />
            <el-option label="成功" value="success" />
            <el-option label="其他" value="other" />
          </el-select>
          <el-select 
            v-model="filterGroup" 
            placeholder="分组筛选" 
            clearable 
            @change="fetchAccounts" 
            style="width: 180px; margin-left: 10px;"
          >
            <el-option label="全部分组" value="" />
            <el-option label="未分组" value="null" />
            <el-option 
              v-for="group in groupList" 
              :key="group.id" 
              :label="`${group.name} (${group.account_count})`" 
              :value="group.id" 
            />
          </el-select>
          <el-button @click="fetchAccounts" :icon="Refresh">刷新</el-button>
        </div>
        
        <div class="batch-actions" v-if="selectedAccounts.length > 0">
          <span class="selection-info">已选 {{ selectedAccounts.length }} 项</span>
          
           <el-button-group class="ml-2">
              <el-tooltip content="一键全自动 (登录-检测-验证-订阅)，可选增项安全设置" placement="top">
                 <el-button type="primary" @click="openOneClickDialog">
                   <el-icon><VideoPlay /></el-icon> 一键全自动
                 </el-button>
              </el-tooltip>
           </el-button-group>

          <el-dropdown class="ml-2" trigger="click" @command="handleBatchCommand">
            <el-button type="warning" plain>
              <el-icon class="mr-1"><CreditCard /></el-icon> 验证/绑卡 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="sheerid">SheerID 验证</el-dropdown-item>
                <el-dropdown-item command="bind_card">自动绑卡</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-dropdown class="ml-2" trigger="click" @command="handleSecurityCommand">
            <el-button type="danger" plain>
              <el-icon class="mr-1"><Lock /></el-icon> 安全设置 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="change_2fa">修改 2FA</el-dropdown-item>
                <el-dropdown-item command="change_recovery">修改辅助邮箱</el-dropdown-item>
                <el-dropdown-item command="get_backup_codes">获取备份码</el-dropdown-item>
                <el-dropdown-item command="one_click_update" divided>一键安全更新</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <el-dropdown class="ml-2" trigger="click" @command="handleSubscriptionCommand">
            <el-button type="info" plain>
              <el-icon class="mr-1"><Monitor /></el-icon> 订阅管理 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="verify_status">验证订阅状态</el-dropdown-item>
                <el-dropdown-item command="click_subscribe">点击订阅按钮</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-card>

    <el-card shadow="hover">
      <el-table 
        :data="accounts" 
        v-loading="loading" 
        stripe 
        @selection-change="handleSelectionChange"
        row-key="id"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" sortable />
        <el-table-column prop="email" label="邮箱" width="280" show-overflow-tooltip>
          <template #default="{ row }">
            <el-link type="primary" :underline="false" @click="viewAccount(row)">
              {{ row.email }}
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column label="分组" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.group_name" type="warning" effect="plain" size="small">
              {{ row.group_name }}
            </el-tag>
            <span v-else class="text-gray-400">未分组</span>
          </template>
        </el-table-column>
        
        <!-- 列表收敛：分类/状态/SheerID/Gemini订阅 移到详情弹窗展示 -->

        <el-table-column label="New-2FA" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="flex flex-col items-start">
              <code v-if="row.new_2fa_display || row.new_2fa" class="mono">{{ format2fa(row.new_2fa_display || row.new_2fa) }}</code>
              <span v-else class="text-gray-500">-</span>
              <span v-if="row.new_2fa_updated_at" class="text-xs text-gray-500 mt-1">
                {{ formatDate(row.new_2fa_updated_at) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Geek" width="110">
           <template #default="{ row }">
              <div class="flex flex-col items-start gap-1">
                 <el-tag v-if="row.geekez_profile_exists" type="primary" size="small" effect="plain">已创建</el-tag>
                 <el-tag v-else type="info" size="small" effect="plain">未创建</el-tag>
                 
                 <el-tag v-if="row.geekez_env" type="success" size="small" effect="dark">
                   已打开 {{ row.geekez_env.debug_port || '' }}
                 </el-tag>
              </div>
           </template>
        </el-table-column>
        <el-table-column label="绑卡" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.card_bound" color="#67c23a" :size="18"><Check /></el-icon>
            <el-icon v-else color="#909399" :size="18"><Close /></el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleLaunchGeekez(row)">{{ getGeekezActionLabel(row) }}</el-button>
            <el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="viewTasks(row)">任务日志</el-button>
            <el-button link type="danger" size="small" @click="deleteAccount(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchAccounts"
        @current-change="fetchAccounts"
        class="mt-4"
      />
    </el-card>

    <!-- 添加账号对话框 -->
    <el-dialog v-model="showDialog" title="添加Google账号" width="500px">
      <el-form :model="accountForm" label-width="100px">
        <el-form-item label="邮箱" required>
          <el-input v-model="accountForm.email" placeholder="请输入Google邮箱" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="accountForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="恢复邮箱">
          <el-input v-model="accountForm.recovery_email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="accountForm.notes" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddAccount" :loading="submitting">添加</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showImportDialog" title="批量导入Google账号" width="700px">
      <el-alert
        title="导入格式说明"
        type="info"
        :closable="false"
        show-icon
        class="mb-4"
      >
        <p>每行一个账号，格式：<code>email----password----recovery----secret</code></p>
        <p>示例：<code>test@gmail.com----Pass123----recovery@mail.com----</code></p>
        <p style="color: #909399; font-size: 12px;">注意：使用 ---- 分隔各字段，恢复邮箱和密钥可留空</p>
      </el-alert>
      
      <el-form :model="importForm" label-width="120px">
        <el-form-item label="分组名称">
          <el-input 
            v-model="importForm.group_name" 
            placeholder="可选，如：售后、2FA（留空则使用当前时间）"
            clearable
          />
          <div class="text-xs text-gray-400 mt-1">
            导入后自动创建分组，如"售后_10个"或"2025-01-25_1030_10个"
          </div>
        </el-form-item>
        <el-form-item label="账号列表">
          <el-input
            v-model="importText"
            type="textarea"
            :rows="12"
            placeholder="粘贴账号数据，每行一个账号"
          />
        </el-form-item>
        <el-form-item label="覆盖已存在">
          <el-switch v-model="importForm.overwrite_existing" />
          <span class="ml-2 text-sm text-gray-500">开启后将更新已存在的账号</span>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="handleImportAccounts" :loading="importing">
          导入 ({{ importCount }} 个账号)
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑账号对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑Google账号" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="邮箱">
           <el-input v-model="editForm.email" disabled />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="editForm.password" type="password" placeholder="留空则不修改" show-password />
        </el-form-item>
        <el-form-item label="恢复邮箱">
          <el-input v-model="editForm.recovery_email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="2FA 密钥">
           <el-input v-model="editForm.secret_key" placeholder="选填" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.notes" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEditAccount" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查看账号详情对话框 -->
    <el-dialog v-model="showViewDialog" title="账号详情" width="600px">
      <el-descriptions v-if="selectedAccount" :column="2" border>
        <el-descriptions-item label="ID">{{ selectedAccount.id }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ selectedAccount.email }}</el-descriptions-item>

        <el-descriptions-item label="分组">
          <el-tag v-if="selectedAccount.group_name" type="warning" effect="plain">
            {{ selectedAccount.group_name }}
          </el-tag>
          <span v-else class="text-gray-500">未分组</span>
        </el-descriptions-item>
        <el-descriptions-item label="分类">
          <el-tag :type="getDerivedTypeTag(selectedAccount.type_tag || '')" effect="dark" size="small">
            {{ selectedAccount.type_display || selectedAccount.type_tag || '-' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(selectedAccount.status)">
            {{ selectedAccount.status_display || selectedAccount.status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="SheerID状态">
          <el-tag :type="selectedAccount.sheerid_verified ? 'success' : 'info'">
            {{ selectedAccount.sheerid_verified ? '已验证' : '未验证' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Gemini状态">
          <el-tag :type="getGeminiStatusType(selectedAccount.gemini_status || '')">
            {{ getGeminiStatusText(selectedAccount.gemini_status || 'not_subscribed') }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="是否绑卡">
          <el-tag :type="selectedAccount.card_bound ? 'success' : 'info'">
            {{ selectedAccount.card_bound ? '已绑卡' : '未绑卡' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="恢复邮箱" :span="2">
          {{ selectedAccount.recovery_email || '无' }}
        </el-descriptions-item>
        <el-descriptions-item label="SheerID链接" :span="2">
          <el-link v-if="selectedAccount.sheerid_link" :href="selectedAccount.sheerid_link" type="primary" target="_blank">
            {{ selectedAccount.sheerid_link }}
          </el-link>
          <span v-else class="text-gray-500">无</span>
        </el-descriptions-item>
        <el-descriptions-item label="最后登录" :span="2">
          {{ selectedAccount.last_login_at ? formatDate(selectedAccount.last_login_at) : '从未登录' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">
          {{ formatDate(selectedAccount.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">
          {{ selectedAccount.notes || '无' }}
        </el-descriptions-item>

        <el-descriptions-item label="New-2FA" :span="2">
          <template v-if="selectedAccount.new_2fa_display || selectedAccount.new_2fa">
            <code class="mono">{{ format2fa(selectedAccount.new_2fa_display || selectedAccount.new_2fa) }}</code>
            <span v-if="selectedAccount.new_2fa_updated_at" class="ml-2 text-xs text-gray-500">
              {{ formatDate(selectedAccount.new_2fa_updated_at) }}
            </span>
          </template>
          <template v-else>
            -
          </template>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 任务日志抽屉 -->
    <el-drawer v-model="showTasksDrawer" title="任务记录" size="900px">
      <div v-if="drawerLoading" class="p-4 text-center">
        <el-icon class="mr-1"><Loading /></el-icon> 加载中...
      </div>
      <div v-else class="drawer-content">
          <el-table :data="accountTasks.tasks" stripe border size="small" row-key="record_id">
            <el-table-column label="来源" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.source === 'google'" type="primary" effect="light" size="small">任务</el-tag>
                <el-tag v-else type="info" effect="light" size="small">任务</el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="name" label="类型" min-width="180" show-overflow-tooltip />

            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <template v-if="row.source === 'google'">
                  <el-tag
                    :type="row.status === 'completed' ? 'success' : (row.status === 'failed' ? 'danger' : (row.status === 'cancelled' ? 'info' : 'warning'))"
                    size="small"
                  >
                    {{ row.status_display || row.status }}
                  </el-tag>
                </template>
                <template v-else>
                  <el-tag
                    v-if="row.state"
                    :type="row.state === 'SUCCESS' ? 'success' : (row.state === 'FAILURE' ? 'danger' : (row.state === 'REVOKED' ? 'info' : 'warning'))"
                    size="small"
                  >
                    {{ row.state }}
                  </el-tag>
                  <span v-else>-</span>
                </template>
              </template>
            </el-table-column>

            <el-table-column label="进度" width="90">
              <template #default="{ row }">
                <span v-if="row.source === 'google'">{{ row.progress_percentage ?? 0 }}%</span>
                <span v-else>-</span>
              </template>
            </el-table-column>

            <el-table-column label="步骤" width="160">
              <template #default="{ row }">
                <span v-if="row.source === 'google' && row.task_type === 'one_click'">
                  {{ row.main_flow_step_num ? `${row.main_flow_step_num}/6` : '-' }}
                  <span class="ml-1 text-gray-500">{{ row.main_flow_step_title || '' }}</span>
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>

            <el-table-column label="增项" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                <div v-if="row.source === 'google' && row.task_type === 'one_click' && Array.isArray(row.main_flow_extras) && row.main_flow_extras.length > 0" class="flex gap-1 flex-wrap">
                  <el-tag v-for="ex in row.main_flow_extras" :key="ex" type="warning" size="small" effect="light">{{ ex }}</el-tag>
                </div>
                <span v-else>-</span>
              </template>
            </el-table-column>

            <el-table-column prop="created_at" label="时间" width="170">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.source === 'google'"
                  link
                  type="primary"
                  size="small"
                  @click="viewTaskLog(row.google_task_id)"
                >
                  日志
                </el-button>
                <el-button
                  v-else
                  link
                  type="primary"
                  size="small"
                  @click="openCeleryTask(String(row.celery_task_id))"
                >
                  日志
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider />

          <el-table :data="accountTasks.task_accounts" stripe border size="small">
            <el-table-column prop="task_id" label="任务ID" width="90" />
            <el-table-column prop="status_display" label="账号状态" width="110" />
            <el-table-column prop="result_message" label="结果" min-width="220" show-overflow-tooltip />
            <el-table-column prop="error_message" label="错误" min-width="220" show-overflow-tooltip />
          </el-table>
      </div>
    </el-drawer>

    <!-- 通用日志查看Dialog -->
    <el-dialog v-model="showLogDialog" title="任务日志" width="800px">
      <div v-if="currentSteps.length > 0" class="mb-4 p-4 bg-gray-50 rounded">
         <el-steps :active="activeStep" finish-status="success" align-center>
            <el-step v-for="(step, index) in currentSteps" :key="index" :title="step.title" :description="step.time" />
         </el-steps>
         
         <div v-if="currentLogExtras.length > 0" class="mt-4 flex gap-2 justify-center">
            <el-tag v-for="extra in currentLogExtras" :key="extra" type="warning" effect="dark">{{ extra }}</el-tag>
         </div>
      </div>

       <div class="log-container">
          <pre>{{ currentLogContent }}</pre>
       </div>
    </el-dialog>

    <!-- Celery 任务：实时 trace 日志（滚动 + 轮询） -->
    <el-dialog
      v-model="showCeleryDialog"
      :title="celeryDialogTitle"
      width="980px"
      @closed="onCeleryDialogClosed"
    >
      <div class="celery-status" v-loading="celeryStatusLoading">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任务ID">{{ celeryTaskId }}</el-descriptions-item>
          <el-descriptions-item label="账号">{{ celeryEmail }}</el-descriptions-item>
          <el-descriptions-item label="state">
            <el-tag size="small">{{ celeryState || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="trace_file">
            <span class="trace-path">{{ traceFile || '-' }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <div class="mt-3 flex gap-2 justify-end">
          <el-button size="small" @click="refreshCeleryStatus">刷新状态</el-button>
          <el-button size="small" type="primary" @click="reloadTrace">重载日志</el-button>
        </div>

        <el-collapse class="mt-3">
          <el-collapse-item title="状态详情" name="status">
            <pre class="status-pre">{{ celeryStatusText }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>

      <el-divider />

      <div class="trace-toolbar">
        <div class="left">
          <el-switch
            v-model="traceFollowLatest"
            active-text="跟随最新"
            inactive-text="停止跟随"
          />
          <span class="trace-hint">向上滚动加载历史；滚动离开底部会自动停止跟随</span>
        </div>
        <div class="right">
          <el-button size="small" @click="copyTrace">复制</el-button>
          <el-button size="small" @click="clearTrace">清空</el-button>
        </div>
      </div>

      <div
        ref="traceScrollRef"
        class="trace-container"
        @scroll="onTraceScroll"
      >
        <div v-if="traceLoadingOlder" class="trace-loader">加载更早日志...</div>
        <div v-else-if="traceHasMoreBackward" class="trace-loader trace-loader-idle">继续上滑加载更早日志</div>

        <div class="trace-lines">
          <div
            v-for="ln in traceLines"
            :key="ln.id"
            class="trace-line"
            :class="{ json: ln.isJson }"
          >{{ ln.text }}</div>
        </div>
      </div>
    </el-dialog>

    <!-- 一键全自动配置（主流程增项） -->
    <el-dialog v-model="showOneClickDialog" title="一键全自动" width="520px">
      <el-alert
        type="info"
        :closable="false"
        class="mb-4"
        title="主流程：登录账号 -> 打开 Google One -> 检查学生资格 -> 学生验证 -> 订阅服务 -> 完成处理"
      />
      <el-form :model="oneClickForm" label-width="140px">
        <el-form-item label="增项：修改2FA">
          <el-switch v-model="oneClickForm.security_change_2fa" />
        </el-form-item>
        <el-form-item label="增项：修改辅助邮箱">
          <el-input v-model="oneClickForm.security_new_recovery_email" placeholder="可选，不填则不修改" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showOneClickDialog = false">取消</el-button>
        <el-button type="primary" @click="submitOneClickTask">开始执行</el-button>
      </template>
    </el-dialog>

    <!-- SheerID 验证配置 Dialog -->
     <el-dialog v-model="showSheerIDDialog" title="SheerID 批量验证" width="500px">
        <el-form :model="sheerIDForm" label-width="100px">
           <el-form-item label="学生姓名" required>
              <el-input v-model="sheerIDForm.student_name" placeholder="如: John Doe" />
           </el-form-item>
           <el-form-item label="学生邮箱" required>
              <el-input v-model="sheerIDForm.student_email" placeholder="如: student@edu.com" />
           </el-form-item>
           <el-form-item label="学校名称" required>
              <el-input v-model="sheerIDForm.school_name" placeholder="如: University of ..." />
           </el-form-item>
        </el-form>
        <template #footer>
           <el-button @click="showSheerIDDialog = false">取消</el-button>
           <el-button type="primary" @click="submitSheerIDTask">开始验证</el-button>
        </template>
     </el-dialog>

    <!-- 自动绑卡配置 Dialog -->
     <el-dialog v-model="showBindCardDialog" title="自动绑卡" width="500px">
        <el-form :model="bindCardForm" label-width="120px">
           <el-alert title="注意：将自动从卡池中分配卡片进行绑定" type="warning" show-icon :closable="false" class="mb-4" />
           <el-form-item label="卡池">
             <el-select v-model="bindCardForm.card_pool" style="width: 180px">
               <el-option label="公共卡池" value="public" />
               <el-option label="私有卡池" value="private" />
             </el-select>
           </el-form-item>
           <el-form-item label="策略">
             <el-select v-model="bindCardForm.card_strategy" style="width: 180px">
               <el-option label="顺序" value="sequential" />
               <el-option label="并发" value="parallel" />
             </el-select>
           </el-form-item>
        </el-form>
        <template #footer>
           <el-button @click="showBindCardDialog = false">取消</el-button>
           <el-button type="primary" @click="submitBindCardTask">开始绑卡</el-button>
        </template>
     </el-dialog>

    <!-- 安全设置 - 修改辅助邮箱 -->
    <el-dialog v-model="showRecoveryEmailDialog" title="修改辅助邮箱" width="500px">
       <el-form label-width="100px">
          <el-form-item label="新辅助邮箱" required>
             <el-input v-model="newRecoveryEmail" placeholder="请输入新的辅助邮箱" />
          </el-form-item>
       </el-form>
       <template #footer>
          <el-button @click="showRecoveryEmailDialog = false">取消</el-button>
          <el-button type="primary" @click="submitChangeRecoveryEmail">确定修改</el-button>
       </template>
    </el-dialog>
    
    <!-- 订阅验证选项 -->
    <el-dialog v-model="showVerifySubDialog" title="验证订阅状态" width="400px">
       <el-form label-width="100px">
          <el-form-item label="开启截图">
             <el-switch v-model="verifySubScreenshot" active-text="截图保存" inactive-text="不截图" />
          </el-form-item>
       </el-form>
       <template #footer>
          <el-button @click="showVerifySubDialog = false">取消</el-button>
          <el-button type="primary" @click="submitVerifyStatus">开始验证</el-button>
       </template>
    </el-dialog>

  </div>
</template>


<script setup lang="ts">
import { ref, reactive, onMounted, computed, nextTick, watch, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Plus, Upload, Check, Close, Refresh, VideoPlay, CreditCard, Lock, 
  Monitor, ArrowDown, Loading, Download
} from '@element-plus/icons-vue'
import { 
  googleAccountsApi, googleTasksApi, googleSecurityApi, 
  googleSubscriptionApi, googleCeleryTasksApi, googleGroupsApi 
} from '@/api/google'
import type { GoogleAccount } from '@/types'

const loading = ref(false)
const submitting = ref(false)
const importing = ref(false)
const accounts = ref<GoogleAccount[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showDialog = ref(false)
const showImportDialog = ref(false)
const showEditDialog = ref(false)
const showViewDialog = ref(false)
const selectedAccount = ref<GoogleAccount | null>(null)
const importText = ref('')
const filterType = ref('')
const filterGroup = ref<string | number>('')
const groupList = ref<Array<{id: number | null, name: string, account_count: number}>>([])
const selectedAccounts = ref<GoogleAccount[]>([])

// Dialog visibility
const showTasksDrawer = ref(false)
const showLogDialog = ref(false)
const showCeleryDialog = ref(false)
const showSheerIDDialog = ref(false)
const showBindCardDialog = ref(false)
const showRecoveryEmailDialog = ref(false)
const showVerifySubDialog = ref(false)
const showOneClickDialog = ref(false)

// Data for dialogs
const drawerLoading = ref(false)
const accountTasks = reactive({
  // 统一任务列表（后端 accounts/{id}/tasks/ 返回 tasks 字段）
  tasks: [] as any[],
  // 账号在 GoogleTask 中的执行明细
  task_accounts: [] as any[]
})
const currentLogContent = ref('')
const currentSteps = ref<any[]>([])
const currentLogExtras = ref<string[]>([])
const activeStep = ref(0)

type TraceLine = { id: number; text: string; isJson: boolean }

const celeryTaskId = ref('')
const celeryEmail = ref('')
const celeryState = ref('')
const celeryMeta = ref<any>(null)
const celeryResult = ref<any>(null)
const celeryError = ref('')
const celeryTraceback = ref('')
const celeryStatusLoading = ref(false)

const traceLines = ref<TraceLine[]>([])
const traceHasMoreBackward = ref(false)
const traceCursorBackward = ref<number | null>(null)
const traceCursorForward = ref<number | null>(null)
const traceFollowLatest = ref(true)
const traceLoadingOlder = ref(false)
const tracePollingTimer = ref<number | null>(null)
const traceFile = ref('')
const traceSize = ref(0)
const traceScrollRef = ref<HTMLElement | null>(null)
let traceLineSeq = 0

const celeryDialogTitle = computed(() => {
  const id = celeryTaskId.value ? `#${celeryTaskId.value}` : ''
  const mail = celeryEmail.value ? ` - ${celeryEmail.value}` : ''
  return `Celery 任务日志 ${id}${mail}`
})

const celeryStatusText = computed(() => {
  const parts: string[] = []
  if (celeryState.value) parts.push(`state: ${celeryState.value}`)
  if (celeryMeta.value) parts.push(`meta: ${JSON.stringify(celeryMeta.value, null, 2)}`)
  if (celeryResult.value) parts.push(`result: ${JSON.stringify(celeryResult.value, null, 2)}`)
  if (celeryError.value) parts.push(`error: ${celeryError.value}`)
  if (celeryTraceback.value) parts.push(`traceback: ${celeryTraceback.value}`)
  return parts.join('\n\n')
})

const stopTracePolling = () => {
  if (tracePollingTimer.value) {
    window.clearInterval(tracePollingTimer.value)
    tracePollingTimer.value = null
  }
}

const startTracePolling = () => {
  stopTracePolling()
  tracePollingTimer.value = window.setInterval(async () => {
    if (!showCeleryDialog.value) return
    if (!traceFollowLatest.value) return
    await fetchTraceForward()
  }, 1000)
}

watch(traceFollowLatest, (v) => {
  if (!showCeleryDialog.value) return
  if (v) startTracePolling()
  else stopTracePolling()
})

onBeforeUnmount(() => {
  stopTracePolling()
})

const sheerIDForm = reactive({
  student_name: '',
  student_email: '',
  school_name: '',
})

const bindCardForm = reactive({
  card_pool: 'public',
  card_strategy: 'sequential'
})

const oneClickForm = reactive({
  security_change_2fa: false,
  security_new_recovery_email: ''
})

const newRecoveryEmail = ref('')
const verifySubScreenshot = ref(false)

const accountForm = reactive({
  email: '',
  password: '',
  recovery_email: '',
  notes: ''
})

const editForm = reactive({
  id: 0,
  email: '',
  password: '',
  recovery_email: '',
  secret_key: '',
  notes: ''
})

const importForm = reactive({
  overwrite_existing: false,
  group_name: ''
})

const importCount = computed(() => {
  if (!importText.value.trim()) return 0
  return importText.value.trim().split('\n').filter(line => line.trim()).length
})

const fetchAccounts = async () => {
  loading.value = true
  try {
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (filterType.value) {
      params.type_tag = filterType.value
    }
    if (filterGroup.value !== '') {
      if (filterGroup.value === 'null') {
        params.group = 'null'  // 未分组
      } else {
        params.group = filterGroup.value
      }
    }
    
    const response = await googleAccountsApi.getAccounts(params)
    // 后端不分页，直接返回数组
    if (Array.isArray(response)) {
      accounts.value = response
      total.value = response.length
    } else if (response.results) {
      // 如果有分页
      accounts.value = response.results
      total.value = response.count || 0
    } else {
      accounts.value = []
      total.value = 0
    }
  } catch (error: any) {
    ElMessage.error('获取账号列表失败: ' + (error.message || '未知错误'))
    accounts.value = []
  } finally {
    loading.value = false
  }
}

const fetchGroups = async () => {
  try {
    const response = await googleGroupsApi.getGroups()
    console.log('fetchGroups response:', response)
    if (Array.isArray(response)) {
      // 过滤掉"未分组"项（前端自己处理）
      groupList.value = response.filter((g: any) => g.id !== null)
      console.log('groupList after filter:', groupList.value)
    } else if (response.data && Array.isArray(response.data)) {
      groupList.value = response.data.filter((g: any) => g.id !== null)
      console.log('groupList after filter (from response.data):', groupList.value)
    } else {
      console.log('Unknown response format:', typeof response, response)
    }
  } catch (error) {
    console.error('获取分组列表失败:', error)
  }
}

const handleSelectionChange = (val: GoogleAccount[]) => {
  selectedAccounts.value = val
}

const getSelectedIds = () => {
  return selectedAccounts.value.map(acc => acc.id)
}

const getGeekezActionLabel = (row: GoogleAccount) => {
  // 统一语义：不存在=创建环境；已存在=打开环境（不再创建）
  return row.geekez_profile_exists ? '打开环境' : '创建环境'
}

const handleLaunchGeekez = async (row: GoogleAccount) => {
    try {
        const res = await googleAccountsApi.launchGeekez(row.id)
        const debugPort = res.data?.debug_port || res.debug_port
        const profileId = res.data?.profile_id || res.profile_id
        const createdProfile = res.data?.created_profile ?? res.created_profile
        
        let msg = createdProfile ? '环境创建并打开成功' : '环境打开成功'
        if (debugPort) msg += `, 端口: ${debugPort}`
        if (profileId) msg += `, Profile: ${profileId}`
        
        ElMessage.success(msg)
        fetchAccounts()
    } catch (e: any) {
        ElMessage.error('操作失败: ' + (e.message || '未知错误'))
    }
}

const openOneClickDialog = async () => {
  if (selectedAccounts.value.length === 0) return
  showOneClickDialog.value = true
}

const submitOneClickTask = async () => {
  if (selectedAccounts.value.length === 0) {
    ElMessage.warning('请先选择账号')
    return
  }

  const config: any = {}
  if (oneClickForm.security_change_2fa) {
    config.security_change_2fa = true
  }
  if (oneClickForm.security_new_recovery_email && oneClickForm.security_new_recovery_email.trim()) {
    config.security_new_recovery_email = oneClickForm.security_new_recovery_email.trim()
  }

  try {
    await googleTasksApi.createTask({
      task_type: 'one_click',
      account_ids: getSelectedIds(),
      config
    })
    ElMessage.success('任务已创建')
    showOneClickDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建任务失败: ' + (e.message || '未知错误'))
  }
}

const handleBatchCommand = (command: string) => {
  if (selectedAccounts.value.length === 0) return
  
  if (command === 'sheerid') {
    showSheerIDDialog.value = true
  } else if (command === 'bind_card') {
    showBindCardDialog.value = true
  }
}

const handleExportCommand = async (command: string) => {
    try {
        const ids = selectedAccounts.value.length > 0 ? getSelectedIds() : []
        let response
        let filename = 'accounts'
        
        if (command === 'csv') {
            response = await googleAccountsApi.exportCsv(ids)
            filename += '.csv'
        } else if (command === 'txt') {
            response = await googleAccountsApi.exportTxt(ids)
            filename += '.txt'
        } else {
            return
        }
        
        // Handle Blob download
        const blob = response instanceof Blob ? response : new Blob([response])
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', filename)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        
        ElMessage.success('导出成功')
    } catch (e: any) {
        console.error(e)
        ElMessage.error('导出失败: ' + (e.message || '未知错误'))
    }
}

const handleSecurityCommand = async (command: string) => {
  if (selectedAccounts.value.length === 0) return
  const ids = getSelectedIds()

  try {
    if (command === 'change_2fa') {
      await ElMessageBox.confirm('确定修改 2FA 密钥吗？将自动生成新密钥。', '修改 2FA')
      await googleSecurityApi.change2fa({ account_ids: ids })
      ElMessage.success('任务已提交')
    } else if (command === 'change_recovery') {
      newRecoveryEmail.value = ''
      showRecoveryEmailDialog.value = true
    } else if (command === 'get_backup_codes') {
      await ElMessageBox.confirm('确定获取备份验证码吗？', '获取备份码')
      await googleSecurityApi.getBackupCodes({ account_ids: ids })
      ElMessage.success('任务已提交')
    } else if (command === 'one_click_update') {
      await ElMessageBox.confirm('确定执行一键安全更新（修改密码/辅助邮箱/2FA）吗？', '一键安全更新', { type: 'warning' })
      await googleSecurityApi.oneClickUpdate({ account_ids: ids })
      ElMessage.success('任务已提交')
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('操作失败: ' + (e.message || '未知错误'))
  }
}

const handleSubscriptionCommand = async (command: string) => {
  if (selectedAccounts.value.length === 0) return
  const ids = getSelectedIds()
  
  try {
    if (command === 'verify_status') {
      showVerifySubDialog.value = true
    } else if (command === 'click_subscribe') {
      await ElMessageBox.confirm('确定执行点击订阅操作吗？', '点击订阅')
      await googleSubscriptionApi.clickSubscribe({ account_ids: ids })
      ElMessage.success('任务已提交')
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('操作失败: ' + (e.message || '未知错误'))
  }
}

// 提交任务
const submitSheerIDTask = async () => {
  if (!sheerIDForm.student_name || !sheerIDForm.student_email || !sheerIDForm.school_name) {
    ElMessage.warning('请填写必要信息')
    return
  }
  
  try {
    await googleTasksApi.createTask({
      task_type: 'verify',
      account_ids: getSelectedIds(),
      config: {
        student_name: sheerIDForm.student_name,
        student_email: sheerIDForm.student_email,
        school_name: sheerIDForm.school_name
      }
    })
    ElMessage.success('SheerID 验证任务已创建')
    showSheerIDDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建失败: ' + e.message)
  }
}

const submitBindCardTask = async () => {
  try {
    await googleTasksApi.createTask({
      task_type: 'bind_card',
      account_ids: getSelectedIds(),
      config: { 
        card_pool: bindCardForm.card_pool,
        card_strategy: bindCardForm.card_strategy
      }
    })
    ElMessage.success('绑卡任务已创建')
    showBindCardDialog.value = false
    fetchAccounts()
  } catch (e: any) {
    ElMessage.error('创建失败: ' + e.message)
  }
}

const submitChangeRecoveryEmail = async () => {
  if (!newRecoveryEmail.value) {
    ElMessage.warning('请输入邮箱')
    return
  }
  try {
    await googleSecurityApi.changeRecoveryEmail({
      account_ids: getSelectedIds(),
      new_email: newRecoveryEmail.value
    })
    ElMessage.success('任务已提交')
    showRecoveryEmailDialog.value = false
  } catch (e: any) {
    ElMessage.error('操作失败: ' + e.message)
  }
}

const submitVerifyStatus = async () => {
  try {
    await googleSubscriptionApi.verifyStatus({
      account_ids: getSelectedIds(),
      take_screenshot: verifySubScreenshot.value
    })
    ElMessage.success('验证任务已提交')
    showVerifySubDialog.value = false
  } catch (e: any) {
    ElMessage.error('操作失败: ' + e.message)
  }
}

// 任务查看
const viewTasks = async (row: GoogleAccount) => {
  showTasksDrawer.value = true
  drawerLoading.value = true
  selectedAccount.value = row
  try {
    const res = await googleAccountsApi.getAccountTasks(row.id)

    const rawTasks = Array.isArray(res.tasks) ? res.tasks : []
    const rawTaskAccounts = Array.isArray(res.task_accounts) ? res.task_accounts : []

    // 对 celery 任务做一次轻量状态补全（仅最近 10 条，避免频繁请求）
    const tasks = [...rawTasks]
    const celeryTasks = tasks.filter(t => t?.source === 'celery' && t?.celery_task_id)
    const recent = celeryTasks.slice(0, 10)
    for (const t of recent) {
      try {
        const st = await googleCeleryTasksApi.getTask(String(t.celery_task_id))
        t.state = st.state
      } catch {
        // ignore
      }
    }

    accountTasks.tasks = tasks
    accountTasks.task_accounts = rawTaskAccounts
  } catch (e) {
    ElMessage.error('获取任务记录失败')
  } finally {
    drawerLoading.value = false
  }
}

const viewTaskLog = async (taskId: number) => {
  try {
    const res = await googleTasksApi.getTaskLog(taskId)
    // 后端返回：{ task_id, log }
    const logStr = typeof res?.log === 'string' ? res.log : JSON.stringify(res, null, 2)
    currentLogContent.value = logStr
    
    // Parse steps
    currentSteps.value = []
    currentLogExtras.value = []
    activeStep.value = 0
    
    // Define standard steps
    const standardSteps = [
        '登录账号', '打开 Google One', '检查学生资格', '学生验证', '订阅服务', '完成处理'
    ]
    
    // Find highest step reached
    let maxStep = 0
    const stepRegex = /步骤 (\d+)\/6:\s*(.*)/g
    let match
    while ((match = stepRegex.exec(logStr)) !== null) {
        const stepNum = parseInt(match[1])
        if (stepNum > maxStep) maxStep = stepNum
    }
    
    // el-steps 的 active 是索引（0-based），日志里是 1-based
    activeStep.value = maxStep > 0 ? Math.min(maxStep - 1, 5) : 0
    currentSteps.value = standardSteps.map(s => ({ title: s, time: '' }))
    
    // Check extras
    const extraRegex = /增项:\s*(.*)/g
    while ((match = extraRegex.exec(logStr)) !== null) {
        if (!currentLogExtras.value.includes(match[1])) {
            currentLogExtras.value.push(match[1])
        }
    }

    showLogDialog.value = true
  } catch (e) {
    ElMessage.error('获取日志失败')
  }
}

const refreshCeleryStatus = async () => {
  if (!celeryTaskId.value) return
  celeryStatusLoading.value = true
  try {
    const res = await googleCeleryTasksApi.getTask(celeryTaskId.value)
    celeryState.value = res?.state || ''
    celeryMeta.value = res?.meta || null
    celeryResult.value = res?.result || null
    celeryError.value = res?.error || ''
    celeryTraceback.value = res?.traceback || ''
  } catch (e) {
    ElMessage.error('查询任务状态失败')
  } finally {
    celeryStatusLoading.value = false
  }
}

const normalizeTraceLines = (raw: string[]): TraceLine[] => {
  const out: TraceLine[] = []
  for (const t of raw || []) {
    const text = String(t ?? '')
    if (!text) continue
    out.push({
      id: ++traceLineSeq,
      text,
      isJson: text.trim().startsWith('{')
    })
  }
  return out
}

const fetchTraceBackward = async (opts?: { initial?: boolean }) => {
  if (!celeryTaskId.value || !celeryEmail.value) return
  if (traceLoadingOlder.value) return
  traceLoadingOlder.value = true

  const initial = Boolean(opts?.initial)
  const scrollEl = traceScrollRef.value
  const prevHeight = scrollEl?.scrollHeight || 0
  const prevTop = scrollEl?.scrollTop || 0

  try {
    const params: any = {
      email: celeryEmail.value,
      direction: 'backward',
      limit_bytes: 262144
    }
    if (!initial && traceCursorBackward.value !== null) {
      params.cursor = traceCursorBackward.value
    }
    const res = await googleCeleryTasksApi.trace(celeryTaskId.value, params)

    traceFile.value = res?.trace_file || traceFile.value
    traceSize.value = typeof res?.size === 'number' ? res.size : traceSize.value
    traceHasMoreBackward.value = Boolean(res?.has_more)
    traceCursorBackward.value = typeof res?.cursor_out === 'number' ? res.cursor_out : traceCursorBackward.value

    // 初次加载：forward cursor 直接定位到 EOF，后续轮询只拿新增
    if (initial) {
      traceCursorForward.value = traceSize.value
    }

    const newLines = normalizeTraceLines(Array.isArray(res?.lines) ? res.lines : [])
    if (newLines.length > 0) {
      traceLines.value = [...newLines, ...traceLines.value]
    }

    await nextTick()

    if (scrollEl) {
      if (initial) {
        scrollEl.scrollTop = scrollEl.scrollHeight
      } else {
        const newHeight = scrollEl.scrollHeight
        scrollEl.scrollTop = newHeight - prevHeight + prevTop
      }
    }
  } catch (e) {
    ElMessage.error('读取 trace 日志失败')
  } finally {
    traceLoadingOlder.value = false
  }
}

const fetchTraceForward = async () => {
  if (!celeryTaskId.value || !celeryEmail.value) return
  const cursor = traceCursorForward.value
  const params: any = {
    email: celeryEmail.value,
    direction: 'forward',
    limit_bytes: 262144
  }
  if (typeof cursor === 'number') params.cursor = cursor

  try {
    const res = await googleCeleryTasksApi.trace(celeryTaskId.value, params)
    traceFile.value = res?.trace_file || traceFile.value
    traceSize.value = typeof res?.size === 'number' ? res.size : traceSize.value
    traceCursorForward.value = typeof res?.cursor_out === 'number' ? res.cursor_out : traceCursorForward.value

    const raw = Array.isArray(res?.lines) ? res.lines : []
    if (raw.length === 0) return

    const newLines = normalizeTraceLines(raw)
    if (newLines.length === 0) return

    traceLines.value = [...traceLines.value, ...newLines]
    await nextTick()

    const el = traceScrollRef.value
    if (el && traceFollowLatest.value) {
      el.scrollTop = el.scrollHeight
    }
  } catch {
    // forward polling：失败不弹窗，避免刷屏
  }
}

const clearTrace = () => {
  traceLines.value = []
}

const copyTrace = async () => {
  try {
    const text = traceLines.value.map(x => x.text).join('\n')
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败（浏览器限制）')
  }
}

const onTraceScroll = async () => {
  const el = traceScrollRef.value
  if (!el) return

  // 顶部：加载更早
  if (el.scrollTop <= 0 && traceHasMoreBackward.value) {
    await fetchTraceBackward({ initial: false })
  }

  // 离开底部：自动停止跟随
  const distanceToBottom = el.scrollHeight - (el.scrollTop + el.clientHeight)
  if (distanceToBottom > 80 && traceFollowLatest.value) {
    traceFollowLatest.value = false
  }
}

const reloadTrace = async () => {
  // 重置游标与内容
  traceLines.value = []
  traceHasMoreBackward.value = false
  traceCursorBackward.value = null
  traceCursorForward.value = null
  traceFile.value = ''
  traceSize.value = 0
  await fetchTraceBackward({ initial: true })
}

const openCeleryTask = async (taskId: string) => {
  const email = selectedAccount.value?.email
  if (!email) {
    ElMessage.error('未找到账号邮箱，无法读取 trace')
    return
  }

  celeryTaskId.value = taskId
  celeryEmail.value = email
  showCeleryDialog.value = true

  // 初始化状态
  celeryState.value = ''
  celeryMeta.value = null
  celeryResult.value = null
  celeryError.value = ''
  celeryTraceback.value = ''

  traceFollowLatest.value = true
  await refreshCeleryStatus()
  await reloadTrace()
  startTracePolling()
}

const onCeleryDialogClosed = () => {
  stopTracePolling()
}

const handleAddAccount = async () => {
  if (!accountForm.email || !accountForm.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }

  submitting.value = true
  try {
    await googleAccountsApi.createAccount(accountForm)
    ElMessage.success('添加成功')
    showDialog.value = false
    Object.assign(accountForm, { email: '', password: '', recovery_email: '', notes: '' })
    fetchAccounts()
  } catch (error: any) {
    ElMessage.error('添加失败: ' + (error.message || '未知错误'))
  } finally {
    submitting.value = false
  }
}

const openEditDialog = (row: GoogleAccount) => {
    editForm.id = row.id
    editForm.email = row.email
    editForm.password = '' // Don't show password
    editForm.recovery_email = row.recovery_email || ''
    editForm.secret_key = '' // 2FA Secret usually not returned or hidden
    editForm.notes = row.notes || ''
    showEditDialog.value = true
}

const submitEditAccount = async () => {
    submitting.value = true
    try {
        const payload: any = {
            recovery_email: editForm.recovery_email,
            notes: editForm.notes
        }
        if (editForm.password) payload.password = editForm.password
        if (editForm.secret_key) payload.secret_key = editForm.secret_key
        
        await googleAccountsApi.editAccount(editForm.id, payload)
        ElMessage.success('更新成功')
        showEditDialog.value = false
        fetchAccounts()
    } catch (e: any) {
        ElMessage.error('更新失败: ' + (e.message || '未知错误'))
    } finally {
        submitting.value = false
    }
}

const handleImportAccounts = async () => {
  if (!importText.value.trim()) {
    ElMessage.warning('请输入账号数据')
    return
  }

  const lines = importText.value.trim().split('\n').filter(line => line.trim())
  if (lines.length === 0) {
    ElMessage.warning('没有有效的账号数据')
    return
  }

  importing.value = true
  try {
    const response = await googleAccountsApi.importAccounts({
      accounts: lines,
      format: 'email----password----recovery----secret',
      overwrite_existing: importForm.overwrite_existing,
      group_name: importForm.group_name || undefined
    })
    
    if (response.success || (response.created_count !== undefined && response.created_count >= 0)) {
      const created = response.created_count ?? response.data?.created_count ?? response.imported_count ?? 0
      const updated = response.updated_count ?? response.data?.updated_count ?? 0
      const failed = response.failed_count ?? response.data?.failed_count ?? 0
      const skipped = response.skipped_count ?? 0
      const groupInfo = response.group ? ` [分组: ${response.group.name}]` : ''
      
      ElMessage.success(
        `导入完成！新增 ${created} 个，更新 ${updated} 个，跳过 ${skipped} 个，失败 ${failed} 个${groupInfo}`
      )
      showImportDialog.value = false
      importText.value = ''
      importForm.overwrite_existing = false
      importForm.group_name = ''
      fetchAccounts()
    } else {
      ElMessage.error('导入失败: ' + (response.message || '未知错误'))
    }
  } catch (error: any) {
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  } finally {
    importing.value = false
  }
}

const viewAccount = (account: GoogleAccount) => {
  selectedAccount.value = account
  showViewDialog.value = true
}

const deleteAccount = async (account: GoogleAccount) => {
  try {
    await ElMessageBox.confirm(`确定要删除账号 ${account.email} 吗？`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
    await googleAccountsApi.deleteAccount(account.id)
    ElMessage.success('删除成功')
    fetchAccounts()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    'active': 'success',
    'locked': 'danger',
    'disabled': 'info',
    'pending_verify': 'warning',
    'verified': 'success',
    'pending_check': 'info'
  }
  return types[status] || 'info'
}

const getDerivedTypeTag = (tag: string) => {
    const map: Record<string, string> = {
        'ineligible': 'info',
        'unbound_card': 'warning',
        'success': 'success',
        'other': 'info'
    }
    return map[tag] || 'info'
}

const getGeminiStatusType = (status: string) => {
  const types: Record<string, any> = {
    'not_subscribed': 'info',
    'pending': 'warning',
    'active': 'success',
    'expired': 'danger',
    'cancelled': 'info'
  }
  return types[status] || 'info'
}

const getGeminiStatusText = (status: string) => {
  const texts: Record<string, string> = {
    'not_subscribed': '未订阅',
    'pending': '订阅中',
    'active': '已订阅',
    'expired': '已过期',
    'cancelled': '已取消'
  }
  return texts[status] || status
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// New-2FA 展示：去除中间空格（Google 提示 spaces don't matter）
const format2fa = (val?: string | null) => {
  return String(val || '').replace(/\s+/g, '')
}

onMounted(() => {
  fetchAccounts()
  fetchGroups()
})
</script>

<style scoped lang="scss">
.google-accounts-module {
  .module-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding: 0 4px;

    h2 {
      margin: 0;
      font-size: 24px;
      font-weight: 600;
      color: #303133;
    }
  }

  .operation-panel {
    background-color: #fcfcfc;
    border: 1px solid #ebeef5;
    
    .flex-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    
    .filters {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .batch-actions {
      display: flex;
      align-items: center;
      
      .selection-info {
        font-size: 13px;
        color: #606266;
        margin-right: 12px;
        background: #f4f4f5;
        padding: 4px 8px;
        border-radius: 4px;
      }
    }
  }

  .mt-4 {
    margin-top: 16px;
  }

  .mb-4 {
    margin-bottom: 16px;
  }

  .ml-2 {
    margin-left: 8px;
  }
  
  .mr-1 {
    margin-right: 4px;
  }

  .text-sm {
    font-size: 12px;
  }

  .text-gray-500 {
    color: #909399;
  }

  .bg-gray-50 {
    background-color: #f9fafb;
  }
  
  .rounded {
    border-radius: 4px;
  }
  
  .flex-col {
    display: flex;
    flex-direction: column;
  }
  
  .gap-1 {
    gap: 4px;
  }
  
  .items-start {
    align-items: flex-start;
  }

  .log-container {
    max-height: 500px;
    overflow-y: auto;
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 12px;
    border-radius: 4px;
    
    pre {
      white-space: pre-wrap;
      word-wrap: break-word;
      margin: 0;
      font-family: Consolas, Monaco, 'Courier New', monospace;
      font-size: 13px;
    }
  }

  .trace-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;

    .left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .trace-hint {
    font-size: 12px;
    color: #909399;
  }

  .trace-path {
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 12px;
    color: #606266;
  }

  .status-pre {
    max-height: 240px;
    overflow: auto;
    padding: 10px 12px;
    background: #f7f9fc;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .trace-container {
    height: 520px;
    overflow: auto;
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid #ebeef5;
    background: #0b1020;
    color: #dbe7ff;
  }

  .trace-loader {
    position: sticky;
    top: 0;
    padding: 6px 8px;
    font-size: 12px;
    color: rgba(219, 231, 255, 0.9);
    background: rgba(11, 16, 32, 0.85);
    border-bottom: 1px solid rgba(219, 231, 255, 0.12);
    z-index: 1;
  }

  .trace-loader-idle {
    opacity: 0.75;
  }

  .trace-lines {
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .trace-line {
    padding: 1px 0;

    &.json {
      color: rgba(219, 231, 255, 0.55);
    }
  }

  code {
    background: #f4f4f5;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    color: #e96900;
  }

  .mono {
    font-family: Consolas, Monaco, 'Courier New', monospace;
    font-size: 12px;
  }
}
</style>
