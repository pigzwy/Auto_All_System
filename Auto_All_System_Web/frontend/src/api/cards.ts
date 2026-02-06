import request from './request'
import type { Card, PaginatedResponse, CardCreateForm } from '@/types'

// 账单地址类型
export interface BillingAddress {
  address_line1: string
  city: string
  state: string
  postal_code: string
  country: string
  cardholder_name?: string
}

// 激活卡响应类型
export interface RedeemCardResponse {
  code: number
  message: string
  data: Card | null
}

// 查询卡响应类型
export interface QueryCardResponse {
  code: number
  message: string
  data: any
}

// 卡密API配置类型
export interface CardApiConfig {
  id: number
  name: string
  redeem_url: string
  query_url: string
  request_method: string
  request_headers: Record<string, string>
  request_body_template: Record<string, any>
  response_mapping: Record<string, any>
  is_active: boolean
  is_default: boolean
  timeout: number
  notes: string
  created_at: string
  updated_at: string
}

export const cardsApi = {
  // 获取虚拟卡列表
  getCards(params?: any): Promise<PaginatedResponse<Card>> {
    return request.get('/cards/', { params })
  },

  // 创建虚拟卡
  createCard(data: CardCreateForm): Promise<Card> {
    return request.post('/cards/', data)
  },

  // 获取虚拟卡详情
  getCard(id: number): Promise<Card> {
    return request.get(`/cards/${id}/`)
  },

  // 更新虚拟卡
  updateCard(id: number, data: Partial<CardCreateForm>): Promise<Card> {
    return request.put(`/cards/${id}/`, data)
  },

  // 删除虚拟卡
  deleteCard(id: number): Promise<void> {
    return request.delete(`/cards/${id}/`)
  },

  // 获取可用虚拟卡
  getAvailableCards(params?: any): Promise<Card[]> {
    return request.get('/cards/available/', { params })
  },

  // 获取我的虚拟卡
  getMyCards(): Promise<Card[]> {
    return request.get('/cards/my_cards/')
  },

  // 批量导入虚拟卡
  importCards(data: { 
    cards_data: Array<{
      card_number: string
      card_holder?: string
      expiry_month: number
      expiry_year: number
      cvv: string
      card_type?: string
      notes?: string
      billing_address?: {
        address_line1?: string
        city?: string
        state?: string
        postal_code?: string
        country?: string
      }
    }>, 
    pool_type: string 
  }): Promise<{ 
    total: number
    success: number
    failed: number
    errors: Array<{card_number: string, error: string}>
  }> {
    return request.post('/cards/import_cards/', data)
  },

  // 通过卡密激活获取卡信息
  redeemCard(data: { key_id: string, pool_type?: string, config_id?: number }): Promise<RedeemCardResponse> {
    return request.post('/cards/redeem_card/', data)
  },

  queryCard(data: { key_id: string, config_id?: number }): Promise<QueryCardResponse> {
    return request.post('/cards/query_card/', data)
  },

  // API 配置管理
  getApiConfigs(params?: any): Promise<PaginatedResponse<CardApiConfig>> {
    return request.get('/cards/api-configs/', { params })
  },

  getActiveApiConfigs(): Promise<{ code: number, message: string, data: CardApiConfig[] }> {
    return request.get('/cards/api-configs/active_list/')
  },

  createApiConfig(data: Partial<CardApiConfig>): Promise<CardApiConfig> {
    return request.post('/cards/api-configs/', data)
  },

  updateApiConfig(id: number, data: Partial<CardApiConfig>): Promise<CardApiConfig> {
    return request.put(`/cards/api-configs/${id}/`, data)
  },

  deleteApiConfig(id: number): Promise<void> {
    return request.delete(`/cards/api-configs/${id}/`)
  },

  setDefaultApiConfig(id: number): Promise<{ code: number, message: string, data: CardApiConfig }> {
    return request.post(`/cards/api-configs/${id}/set_default/`)
  }
}
