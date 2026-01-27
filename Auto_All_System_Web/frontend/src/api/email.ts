/**
 * 域名邮箱管理 API
 */

import request from './request'

export interface CloudMailConfig {
  id: number
  name: string
  api_base: string
  api_token?: string
  masked_token?: string
  domains: string[]
  default_role: string
  is_default: boolean
  is_active: boolean
  domains_count: number
  created_at: string
  updated_at: string
}

export interface CloudMailConfigForm {
  name: string
  api_base: string
  api_token: string
  domains: string[]
  default_role: string
  is_default: boolean
  is_active: boolean
}

// 获取配置列表
export const getCloudMailConfigs = () => {
  return request.get<CloudMailConfig[]>('/email/configs/')
}

// 获取单个配置
export const getCloudMailConfig = (id: number) => {
  return request.get<CloudMailConfig>(`/email/configs/${id}/`)
}

// 创建配置
export const createCloudMailConfig = (data: CloudMailConfigForm) => {
  return request.post<CloudMailConfig>('/email/configs/', data)
}

// 更新配置
export const updateCloudMailConfig = (id: number, data: Partial<CloudMailConfigForm>) => {
  return request.patch<CloudMailConfig>(`/email/configs/${id}/`, data)
}

// 删除配置
export const deleteCloudMailConfig = (id: number) => {
  return request.delete(`/email/configs/${id}/`)
}

// 测试连接
export const testCloudMailConnection = (id: number) => {
  return request.post<{ success: boolean; message: string }>(`/email/configs/${id}/test_connection/`)
}

// 测试创建邮箱
export const testCloudMailEmail = (id: number, toEmail: string) => {
  return request.post<{ success: boolean; message: string; data?: { email: string; password: string } }>(
    `/email/configs/${id}/test_email/`,
    { to_email: toEmail }
  )
}

// 设置为默认
export const setDefaultCloudMailConfig = (id: number) => {
  return request.post<{ success: boolean; message: string }>(`/email/configs/${id}/set_default/`)
}

// 获取默认配置
export const getDefaultCloudMailConfig = () => {
  return request.get<CloudMailConfig>('/email/configs/get_default/')
}
