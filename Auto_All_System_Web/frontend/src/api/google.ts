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
  importAccounts(data: { accounts: string[]; format?: string; match_browser?: boolean; overwrite_existing?: boolean }): Promise<ApiResponse<any>> {
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

  // 修改辅助邮箱
  changeRecoveryEmail(data: { account_ids: number[]; new_email: string; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/security/change_recovery_email/', data)
  },

  // 获取备份验证码
  getBackupCodes(data: { account_ids: number[]; browser_type?: string }): Promise<ApiResponse<any>> {
    return request.post('/plugins/google-business/security/get_backup_codes/', data)
  },

  // 一键修改全部
  oneClickUpdate(data: { account_ids: number[]; new_email?: string; browser_type?: string }): Promise<ApiResponse<any>> {
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
  }
}

