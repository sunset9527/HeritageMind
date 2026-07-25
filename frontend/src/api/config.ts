import client from './client'

export interface ServerConfig {
  model: string
  base_url: string
  provider: string
}

export async function getServerConfig(): Promise<ServerConfig> {
  const { data } = await client.get<ServerConfig>('/config')
  return data
}
