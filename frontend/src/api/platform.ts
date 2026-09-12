import client from './client'

export interface CraftEntry { name: string; slug: string; summary: string; content?: string }
export interface Source { name: string; url: string; evidence: string }
export interface Inheritor { name: string; slug: string; craft_name: string; region: string; recognition: string; biography: string; lineage: string; representative_works: string; sources: Source[] }

export async function listEncyclopedia() { return (await client.get<{ items: CraftEntry[] }>('/encyclopedia')).data.items }
export async function getCraft(slug: string) { return (await client.get<CraftEntry>(`/encyclopedia/${encodeURIComponent(slug)}`)).data }
export async function listInheritors() { return (await client.get<{ items: Inheritor[] }>('/inheritors')).data.items }
export async function getInheritor(slug: string) { return (await client.get<Inheritor>(`/inheritors/${encodeURIComponent(slug)}`)).data }
