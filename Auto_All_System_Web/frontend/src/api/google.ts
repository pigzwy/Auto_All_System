import request from './request'
import type { ApiResponse, GoogleAccount, PaginatedResponse } from '@/types'

export const googleAccountsApi = {
  // 获取Google账号列表
  getAccounts(params?: any): Promise<PaginatedResponse<GoogleAccount>> {
    return request.get('/plugins/google-business/accounts/', { params })
  },

  // 获取账号统计
  getStats(): Promise<ApiResponse<any>> {
    return request.get('/plugins/google-business/accounts/stats/')
  },

  // 创建账号
  createAccount(data: Partial<GoogleAccount>): Promise<ApiResponse<GoogleAccount>> {
    return request.post('/plugins/google-business/accounts/', data)
  },

  // 更新账号
  updateAccount(id: number, data: Partial<GoogleAccount>): Promise<ApiResponse<GoogleAccount>> {
    return request.put(`/plugins/google-business/accounts/${id}/`, data)
  },

  // 删除账号
  deleteAccount(id: number): Promise<ApiResponse<any>> {
    return request.delete(`/plugins/google-business/accounts/${id}/`)
  },

  // 批量导入账号
  importAccounts(data: { 
    accounts: string[]; 
    format?: string; 
    match_browser?: boolean; 
    overwrite_existing?: boolean;
    group_name?: string;
    group_id?: number;
  }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/accounts/import_accounts/', data)
  },

  // 批量删除账号
  bulkDeleteAccounts(ids: number[]): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/accounts/bulk_delete/', { ids })
  },

  // SheerID验证
  verifyWithSheerID(id: number): Promise<ApiResponse<any>> {
    return request.post(`/plugins/google-business/accounts/${id}/verify_sheerid/`)
  },

  // 绑定虚拟卡
  bindCard(accountId: number, cardId: number): Promise<ApiResponse<any>> {
    return request.post(`/plugins/google-business/accounts/${accountId}/bind_card/`, { card_id: cardId })
  },

  // 一键自动化
  automate(accountId: number): Promise<ApiResponse<any>> {
    return request.post(`/plugins/google-business/accounts/${accountId}/automate/`)
  },

  // 获取账号关联任务/操作历史（账号管理页使用）
  getAccountTasks(accountId: number): Promise<ApiResponse<any>> {
    return request.get(`/plugins/google-business/accounts/${accountId}/tasks/`)
  },

  // 清空账号的历史任务记录（保留运行中任务，同时删除磁盘文件）
  clearAccountTasks(accountId: number): Promise<{ status: string; removed: number }> {
    return request.delete(`/plugins/google-business/accounts/${accountId}/clear_tasks/`)
  },

  // 启动 Geekez 浏览器环境
  launchGeekez(accountId: number): Promise<ApiResponse<any>> {
    return request.post(`/plugins/google-business/accounts/${accountId}/launch_geekez/`)
  },

  // 编辑账号（支持密码/2FA/恢复邮箱/备注）
  editAccount(accountId: number, data: any): Promise<ApiResponse<any>> {
    return request.patch(`/plugins/google-business/accounts/${accountId}/edit/`, data)
  },

  // 导出 TXT（Blob）
  exportTxt(ids?: number[]): Promise<any> {
    return request.post('/plugins/google-business/accounts/export_txt/', { ids: ids || [] }, { responseType: 'blob' })
  },

  // 导出 CSV（Blob）
  exportCsv(ids?: number[]): Promise<any> {
    return request.post('/plugins/google-business/accounts/export_csv/', { ids: ids || [] }, { responseType: 'blob' })
  }
}

// 账号分组 API
export const googleGroupsApi = {
  // 获取分组列表（带账号数量）
  getGroups(): Promise<any> {
    return request.get('/plugins/google-business/groups/list_with_counts/')
  },

  // 创建分组
  createGroup(data: { name: string; description?: string }): Promise<any> {
    return request.post('/plugins/google-business/groups/', data)
  },

  // 删除分组
  deleteGroup(id: number): Promise<any> {
    return request.delete(`/plugins/google-business/groups/${id}/`)
  },

  // 将账号添加到分组
  addAccountsToGroup(groupId: number, accountIds: number[]): Promise<any> {
    return request.post(`/plugins/google-business/groups/${groupId}/add_accounts/`, { account_ids: accountIds })
  },

  // 从分组移除账号
  removeAccountsFromGroup(groupId: number, accountIds: number[]): Promise<any> {
    return request.post(`/plugins/google-business/groups/${groupId}/remove_accounts/`, { account_ids: accountIds })
  }
}

// Google 任务管理 API（用于 OneClick/SheerID/BindCard 等模块）
// 对应后端：/api/v1/plugins/google-business/tasks/
export const googleTasksApi = {
  // 创建任务
  createTask(data: {
    task_type: string
    account_ids: number[]
    config?: Record<string, any>
  }): Promise<any> {
    return request.post('/plugins/google-business/tasks/', data)
  },

  // 获取任务详情
  getTask(taskId: number | string): Promise<any> {
    return request.get(`/plugins/google-business/tasks/${taskId}/`)
  },

  // 获取任务日志
  getTaskLog(taskId: number | string, params?: Record<string, any>): Promise<any> {
    return request.get(`/plugins/google-business/tasks/${taskId}/log/`, { params })
  },

  // 获取任务账号执行明细
  getTaskAccounts(taskId: number | string, params?: any): Promise<any> {
    return request.get(`/plugins/google-business/tasks/${taskId}/accounts/`, { params })
  },

  // 取消任务（如后端支持）
  cancelTask(taskId: number | string): Promise<any> {
    return request.post(`/plugins/google-business/tasks/${taskId}/cancel/`)
  },

  // 获取任务产物列表
  getTaskArtifacts(taskId: number | string): Promise<any> {
    return request.get(`/plugins/google-business/tasks/${taskId}/artifacts/`)
  }
}

// Google虚拟卡API
export const googleCardsApi = {
  // 获取虚拟卡列表
  getCards(params?: any): Promise<PaginatedResponse<any>> {
    return request.get('/plugins/google-business/cards/', { params })
  },

  // 创建虚拟卡
  createCard(data: any): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/cards/', data)
  },

  // 更新虚拟卡
  updateCard(id: number, data: any): Promise<ApiResponse<any>> {
    return request.put(`/plugins/google-business/cards/${id}/`, data)
  },

  // 删除虚拟卡
  deleteCard(id: number): Promise<ApiResponse<any>> {
    return request.delete(`/plugins/google-business/cards/${id}/`)
  },

  // 批量导入虚拟卡
  importCards(data: { cards_data: string[]; max_usage?: number; pool_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/cards/import_cards/', data)
  }
}

// Google 浏览器管理 API
export const googleBrowserApi = {
  // 获取可用浏览器列表
  getAvailable(): Promise<ApiResponse<any>> {
    return request.get('/plugins/google-business/browser/available/')
  },

  // 获取当前浏览器连接状态（用于前端展示/自检）
  getStatus(): Promise<ApiResponse<any>> {
    return request.get('/plugins/google-business/browser/status/')
  },

  // 设置默认浏览器
  setDefault(data: { browser_type: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/browser/set_default/', data)
  },

  // 获取浏览器池统计
  getPoolStats(): Promise<ApiResponse<any>> {
    return request.get('/plugins/google-business/browser/pool_stats/')
  }
}

// Google 安全设置 API
export const googleSecurityApi = {
  // 修改 2FA 密钥
  change2fa(data: { account_ids: number[]; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/security/change_2fa/', data)
  },

  // 修改辅助邮箱（手动指定邮箱）
  changeRecoveryEmail(data: { account_ids: number[]; new_email: string; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/security/change_recovery_email/', data)
  },

  // 自动创建域名邮箱并换绑辅助邮箱
  autoChangeRecoveryEmail(data: { account_ids: number[]; cloudmail_config_id: number; max_concurrency?: number; stagger_seconds?: number; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/security/auto_change_recovery_email/', data)
  },

  // 获取备份验证码
  getBackupCodes(data: { account_ids: number[]; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/security/get_backup_codes/', data)
  },

  // 一键修改全部
  oneClickUpdate(data: {
    account_ids: number[]
    new_email?: string
    browser_type?: string
    max_concurrency?: number
    stagger_seconds?: number
    rest_min_minutes?: number
    rest_max_minutes?: number
  }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/security/one_click_update/', data)
  }
}

// Google 订阅验证 API
export const googleSubscriptionApi = {
  // 验证订阅状态
  verifyStatus(data: { account_ids: number[]; take_screenshot?: boolean; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/subscription/verify_status/', data)
  },

  // 点击订阅按钮
  clickSubscribe(data: { account_ids: number[]; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/subscription/click_subscribe/', data)
  },

  // 获取订阅验证截图（需要鉴权，返回 Blob）
  getScreenshot(file: string): Promise<any> {
    return request.get('/plugins/google-business/subscription/screenshot/', {
      params: { file },
      responseType: 'blob',
    })
  }
}

// Google Celery 任务查询 API（用于 security/subscription 的 task_id 轮询）
export const googleCeleryTasksApi = {
  getTask(taskId: string): Promise<ApiResponse<any>> {
    return request.get(`/plugins/google-business/celery-tasks/${taskId}/`)
  },

  trace(taskId: string, params: {
    email: string
    account_id?: number
    direction?: 'forward' | 'backward'
    cursor?: number | null
    limit_bytes?: number
  }): Promise<ApiResponse<any>> {
    return request.get(`/plugins/google-business/celery-tasks/${taskId}/trace/`, { params })
  },

  cancel(taskId: string): Promise<ApiResponse<any>> {
    return request.post(`/plugins/google-business/celery-tasks/${taskId}/cancel/`)
  }
}
