import client from './client'
import type { CraftItem, ProfileItem } from '@/types'

export async function getCrafts(): Promise<CraftItem[]> {
  const { data } = await client.get<{ crafts: CraftItem[] }>('/crafts')
  return data.crafts
}

export async function getProfiles(): Promise<ProfileItem[]> {
  const { data } = await client.get<{ profiles: ProfileItem[] }>('/profiles')
  return data.profiles
}

export async function switchProfile(profile: string): Promise<void> {
  await client.post('/switch-profile', { profile })
}

export async function getDocumentSummary(): Promise<any> {
  const { data } = await client.get('/documents/summary')
  return data
}
