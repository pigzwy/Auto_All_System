import request from './request'


export interface GeekezIntegrationConfig {
  control_host: string
  control_port: number
  api_server_host: string
  api_server_port: number
  has_control_token: boolean
}

export interface GeekezConnectionTestResult {
  control: {
    ok: boolean
    base_url: string
    latency_ms: number
    url?: string
    status_code?: number
    attempts?: any[]
    note?: string
    error?: string
  }
  api_server: {
    ok: boolean
    url: string
    latency_ms: number
    status_code?: number
    data?: any
    attempts?: any[]
    note?: string
    error?: string
  }
}

export type GeekezConfigUpdate = Partial<GeekezIntegrationConfig> & {
  control_token?: string
}

export const geekezApi = {
  getConfig(): Promise<GeekezIntegrationConfig> {
    return request.get('/geekez/config/')
  },
  updateConfig(data: GeekezConfigUpdate): Promise<GeekezIntegrationConfig> {
    return request.put('/geekez/config/', data)
  },
  testConnection(data: any): Promise<GeekezConnectionTestResult> {
    return request.post('/geekez/config/test/', data)
  }
}
