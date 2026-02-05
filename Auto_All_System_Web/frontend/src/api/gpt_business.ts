import request from './request'

export interface GptBusinessStatistics {
  teams: number
  accounts: number
  tasks: number
}

export interface GptBusinessInviteTaskCreate {
  flow?: 'invite_only'
  team_name: string
  count?: number
  password?: string
  legacy_args?: string[]
}

export interface GptBusinessActiveTask {
  id?: string
  type?: string
  status?: string
  progress_current?: number
  progress_total?: number
  progress_percent?: number
  progress_label?: string
  created_at?: string
  started_at?: string
}

export type GptBusinessAccountType = 'mother' | 'child'

export interface GptBusinessAccount {
  id: string
  type: GptBusinessAccountType
  parent_id?: string

  cloudmail_config_id?: number
  cloudmail_domain?: string

  email: string
  email_password: string
  account_password?: string

  geekez_profile_exists?: boolean
  geekez_env?: any

  active_task?: GptBusinessActiveTask

  // 状态字段（后端 tasks 会写回；用于前端展示/跳过策略）
  open_status?: string
  register_status?: string
  register_updated_at?: string
  login_status?: string
  login_updated_at?: string
  pool_status?: string
  pool_updated_at?: string
  invite_status?: string
  invite_updated_at?: string
  team_join_status?: string
  team_join_updated_at?: string
  team_account_id?: string

  seat_total?: number
  seat_used?: number
  note?: string
  created_at?: string
  updated_at?: string
}

export interface GptBusinessAccountsResponse {
  mothers: Array<GptBusinessAccount & { children: GptBusinessAccount[] }>
  email_domains: string[]
}

export const gptBusinessApi = {
  getStatistics(): Promise<GptBusinessStatistics> {
    return request.get('/plugins/gpt-business/statistics/')
  },

  getSettings(): Promise<any> {
    return request.get('/plugins/gpt-business/settings/current/')
  },

  updateSettings(data: any): Promise<any> {
    return request.put('/plugins/gpt-business/settings/current/', data)
  },

  listTasks(): Promise<any[]> {
    return request.get('/plugins/gpt-business/tasks/')
  },

  getAccountTasks(motherAccountId: string): Promise<{ tasks: any[] }> {
    return request.get(`/plugins/gpt-business/accounts/${motherAccountId}/tasks/`)
  },

  clearAccountTasks(motherAccountId: string): Promise<{ status: string; removed: number }> {
    return request.delete(`/plugins/gpt-business/accounts/${motherAccountId}/tasks/`)
  },

  createTask(data: GptBusinessInviteTaskCreate): Promise<any> {
    return request.post('/plugins/gpt-business/tasks/', data)
  },

  getTask(taskId: string): Promise<any> {
    return request.get(`/plugins/gpt-business/tasks/${taskId}/`)
  },

  getTaskArtifacts(taskId: string): Promise<Array<{ name: string; download_url: string }>> {
    return request.get(`/plugins/gpt-business/tasks/${taskId}/artifacts/`)
  },

  getTaskLog(
    taskId: string,
    opts?: {
      tail?: number
      filename?: string
    }
  ): Promise<{ filename: string; exists: boolean; text: string; download_url: string }> {
    return request.get(`/plugins/gpt-business/tasks/${taskId}/log/`, {
      params: {
        tail: opts?.tail,
        filename: opts?.filename
      }
    })
  },

  cancelTask(taskId: string): Promise<{ status: string }> {
    return request.post(`/plugins/gpt-business/tasks/${taskId}/cancel/`)
  },

  getCeleryTask(celeryTaskId: string): Promise<any> {
    return request.get(`/plugins/gpt-business/celery-tasks/${celeryTaskId}/`)
  },

  trace(
    celeryTaskId: string,
    params: {
      email?: string
      direction?: 'backward' | 'forward'
      limit_bytes?: number
      cursor?: number
    }
  ): Promise<any> {
    return request.get(`/plugins/gpt-business/celery-tasks/${celeryTaskId}/trace/`, { params })
  },

  listAccounts(): Promise<GptBusinessAccountsResponse> {
    return request.get('/plugins/gpt-business/accounts/')
  },

  createMotherAccounts(data: {
    cloudmail_config_id: number
    domain?: string
    count?: number
    seat_total?: number
    note?: string
  }): Promise<{ created: GptBusinessAccount[] }> {
    return request.post('/plugins/gpt-business/accounts/mothers/', data)
  },

  createChildAccounts(data: {
    parent_id: string
    cloudmail_config_id?: number
    domain?: string
    count?: number
    note?: string
  }): Promise<{ created: GptBusinessAccount[] }> {
    return request.post('/plugins/gpt-business/accounts/children/', data)
  },

  updateAccount(accountId: string, data: { seat_total?: number; note?: string }): Promise<GptBusinessAccount> {
    return request.patch(`/plugins/gpt-business/accounts/${accountId}/`, data)
  },

  deleteAccount(accountId: string): Promise<void> {
    return request.delete(`/plugins/gpt-business/accounts/${accountId}/`)
  },

  selfRegister(motherAccountId: string): Promise<{ message?: string; task_id?: string }> {
    return request.post(`/plugins/gpt-business/accounts/${motherAccountId}/self_register/`)
  },

  batchSelfRegister(data: {
    mother_ids: string[]
    concurrency?: number
    open_geekez?: boolean
  }): Promise<{ message?: string; results?: any[] }> {
    return request.post('/plugins/gpt-business/accounts/batch/self_register/', data)
  },

  autoInvite(motherAccountId: string): Promise<{ message?: string; task_id?: string }> {
    return request.post(`/plugins/gpt-business/accounts/${motherAccountId}/auto_invite/`)
  },

  batchAutoInvite(data: {
    mother_ids: string[]
    concurrency?: number
    open_geekez?: boolean
  }): Promise<{ message?: string; results?: any[] }> {
    return request.post('/plugins/gpt-business/accounts/batch/auto_invite/', data)
  },

  sub2apiSink(
    motherAccountId: string,
    data?: {
      target_key?: string
      mode?: string
    }
  ): Promise<{ message?: string; task_id?: string; record_id?: string; target_key?: string }> {
    return request.post(`/plugins/gpt-business/accounts/${motherAccountId}/sub2api_sink/`, data || {})
  },

  batchSub2apiSink(data: {
    mother_ids: string[]
    concurrency?: number
    open_geekez?: boolean
    target_key?: string
    mode?: string
  }): Promise<{ message?: string; results?: any[] }> {
    return request.post('/plugins/gpt-business/accounts/batch/sub2api_sink/', data)
  },

  launchGeekez(accountId: string): Promise<{
    success: boolean
    created_profile?: boolean
    browser_type?: string
    profile_id?: string
    debug_port?: number
    cdp_endpoint?: string
    ws_endpoint?: string
    pid?: number
    saved?: boolean
  }> {
    return request.post(`/plugins/gpt-business/accounts/${accountId}/launch_geekez/`)
  },

  testS2aConnection(data: {
    target_key?: string
    config?: {
      api_base?: string
      admin_key?: string
      admin_token?: string
      concurrency?: number
      priority?: number
      group_ids?: number[]
      group_names?: string[]
    }
  }): Promise<{ success: boolean; message: string; target_key?: string }> {
    return request.post('/plugins/gpt-business/settings/s2a/test/', data)
  },

  testCrsConnection(data?: {
    config?: {
      api_base?: string
      admin_token?: string
    }
  }): Promise<{ success: boolean; message: string }> {
    return request.post('/plugins/gpt-business/settings/crs/test/', data || {})
  },

  teamPush(
    motherAccountId: string,
    data: {
      target_url: string
      password: string
      is_warranty?: boolean
      seat_total?: number
      note?: string
    }
  ): Promise<{ message?: string; task_id?: string; record_id?: string }> {
    return request.post(`/plugins/gpt-business/accounts/${motherAccountId}/team_push/`, data)
  },
}
