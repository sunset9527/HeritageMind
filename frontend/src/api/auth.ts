import client from './client'
import type { TokenResponse, UserResponse } from '@/types'

export async function login(username: string, password: string): Promise<TokenResponse> {
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)

  const { data } = await client.post<TokenResponse>('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function register(username: string, email: string, password: string): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>('/auth/register', {
    username,
    email,
    password,
  })
  return data
}

export async function getMe(): Promise<UserResponse> {
  const { data } = await client.get<UserResponse>('/auth/me')
  return data
}
