import request from './request'
import type { User } from '@/types'

type UpdateProfilePayload = {
  email?: string
  phone?: string
  avatar?: string
}

type ChangePasswordPayload = {
  old_password: string
  new_password: string
}

export const userApi = {
  getMe(): Promise<User> {
    return request.get('/users/me/')
  },

  updateProfile(payload: UpdateProfilePayload): Promise<User> {
    return request.put('/users/update_profile/', payload)
  },

  changePassword(payload: ChangePasswordPayload): Promise<null> {
    return request.post('/users/change_password/', payload)
  }
}

export default userApi
