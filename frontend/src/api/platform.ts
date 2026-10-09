import client from './client'
import type { AxiosRequestConfig } from 'axios'

export interface CraftImage { url: string | null; status: 'verified' | 'legacy_local' | 'pending_review' | 'extracted' | 'unavailable' }
export interface CraftEntry { name: string; slug: string; summary: string; content?: string; image: CraftImage }
export interface Source { name: string; url: string; evidence: string }
export interface Inheritor { name: string; slug: string; craft_name: string; region: string; recognition: string; biography: string; lineage: string; representative_works: string; sources: Source[] }
export interface DocumentSummary { total_documents: number }
export async function listEncyclopedia(config?: AxiosRequestConfig) { return (await client.get<{ items: CraftEntry[] }>('/encyclopedia', config)).data.items }
export async function getCraft(slug: string, config?: AxiosRequestConfig) { return (await client.get<CraftEntry>(`/encyclopedia/${encodeURIComponent(slug)}`, config)).data }
export async function listInheritors(config?: AxiosRequestConfig) { return (await client.get<{ items: Inheritor[] }>('/inheritors', config)).data.items }
export async function getInheritor(slug: string, config?: AxiosRequestConfig) { return (await client.get<Inheritor>(`/inheritors/${encodeURIComponent(slug)}`, config)).data }
