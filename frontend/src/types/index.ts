// ===== User & Auth =====
export interface UserResponse {
  id: number
  username: string
  email: string
  role: 'user' | 'admin'
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserResponse | null
}

export interface UserRegisterRequest {
  username: string
  email: string
  password: string
}

// ===== Query =====
export interface QueryRequest {
  question: string
  user_profile: string
  include_narrative: boolean
  craft_filter?: string | null
}

export interface SourceAgent {
  id: string
  type: string
  contribution: string
}

export interface DebateRound {
  round_num: number
  agent_name: string
  agent_avatar: string
  role: string
  content: string
  references: string[]
}

export interface DebateSession {
  question: string
  debate_mode: 'progressive' | 'parallel' | 'multi_perspective'
  rounds: DebateRound[]
  final_synthesis: string
  key_insights: string[]
}

export interface Citation {
  title: string
  source?: string
}

export interface QueryResponse {
  question: string
  answer: string
  user_profile: string
  source_agents: SourceAgent[]
  has_gaps: boolean
  gap_report: string
  reading_time: number
  metadata: Record<string, any>
  debate_session?: DebateSession
  citations?: Citation[]
}

// ===== Chat History =====
export interface ChatHistoryItem {
  id: number
  question: string
  answer_preview: string
  user_profile: string
  agents_used: string[] | null
  has_gaps: boolean
  created_at: string
}

export interface ChatHistoryListResponse {
  items: ChatHistoryItem[]
  total: number
}

export interface ChatDetailResponse {
  id: number
  question: string
  answer: string
  user_profile: string
  agents_used: any
  has_gaps: boolean
  created_at: string
}

// ===== Graph =====
export interface GraphStats {
  total_nodes: number
  total_edges: number
  node_types: Record<string, number>
  edge_types: Record<string, number>
}

export interface GraphVisualizeResponse {
  html: string
}

export interface GraphNode {
  id: string
  name: string
  type: string
  properties: Record<string, any>
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
}

export interface SubgraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// ===== Crafts & Profiles =====
export interface CraftItem {
  id: string
  name: string
}

export interface ProfileItem {
  id: string
  name: string
  description: string
  depth: string
}

// ===== Gap Report =====
export interface GapItem {
  aspect: string
  description: string
  suggestion: string
}

export interface GapReport {
  coverage_level: 'sufficient' | 'partial' | 'missing'
  relevant_documents: number
  coverage_score: number
  gaps: GapItem[]
  can_answer: boolean
  suggestions: string[]
  report: string
}

// ===== Chat Message (UI model) =====
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  metadata?: {
    sourceAgents: SourceAgent[]
    debateSession?: DebateSession
    hasGaps: boolean
    gapReport: string
    citations: Citation[]
    elapsedMs: number
    model: string
  }
}

// ===== Agent Meta =====
export interface AgentMeta {
  icon: string
  name: string
  cssClass: string
}

export const AGENT_META_MAP: Record<string, AgentMeta> = {
  craft_expert: { icon: '🎨', name: '技艺专家', cssClass: 'craft' },
  history_expert: { icon: '📜', name: '历史专家', cssClass: 'history' },
  heritage_expert: { icon: '🏛️', name: '传承专家', cssClass: 'heritage' },
  synthesis: { icon: '✨', name: '综合分析', cssClass: 'synthesis' },
}
