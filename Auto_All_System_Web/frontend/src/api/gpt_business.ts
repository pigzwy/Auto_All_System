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

  getCeleryTask(celeryTaskId: string): Promise<any> {
    return request.get(`/plugins/gpt-business/celery-tasks/${celeryTaskId}/`)
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

  autoInvite(motherAccountId: string): Promise<{ message?: string; task_id?: string }> {
    return request.post(`/plugins/gpt-business/accounts/${motherAccountId}/auto_invite/`)
  },

  sub2apiSink(motherAccountId: string): Promise<{ message?: string; task_id?: string }> {
    return request.post(`/plugins/gpt-business/accounts/${motherAccountId}/sub2api_sink/`)
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
  }
}
