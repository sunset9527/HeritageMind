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
  session_id?: string | null
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
  debate_mode: 'progressive' | 'parallel' | 'multi_perspective' | 'dynamic'
  rounds: DebateRound[]
  final_synthesis: string
  key_insights: string[]
}

export interface Citation {
  title: string
  source?: string
}

export interface WorkflowRoute {
  question_type: 'factual' | 'comparative' | 'procedural' | 'open_ended'
  execution_route: 'rag' | 'graph' | 'hybrid'
  use_memory: boolean
  reason: string
  fallback_reason?: string
}

export interface WorkflowTraceEntry {
  node: string
  status: 'completed' | 'skipped' | 'fallback'
  elapsed_ms: number
  message: string
}

export type WorkflowNodeStatus = 'pending' | 'running' | 'completed' | 'skipped' | 'fallback'

export interface RealtimeWorkflowNode {
  id: string
  label: string
  icon?: string
  status: WorkflowNodeStatus
}

export interface RealtimeWorkflowEdge {
  source: string
  target: string
}

export interface CollaborationMessage {
  from_agent: string
  to_agent: string
  kind: 'supplement' | 'challenge' | 'response' | 'agree'
  summary: string
}

export interface RealtimeWorkflow {
  runId: string
  nodes: RealtimeWorkflowNode[]
  edges: RealtimeWorkflowEdge[]
  messages: CollaborationMessage[]
  completed: boolean
}

export interface WorkflowSseEvent {
  event?: string
  run_id?: string
  step: string
  msg: string
  nodes?: Array<{ id: string; label: string; icon?: string }>
  edges?: RealtimeWorkflowEdge[]
  from_agent?: string
  to_agent?: string
  kind?: CollaborationMessage['kind']
  summary?: string
  answer?: string
  source_agents?: SourceAgent[]
  has_gaps?: boolean
  gap_report?: string
  session_id?: string | null
  workflow_trace?: WorkflowTraceEntry[]
  citations?: Citation[]
  collaboration_messages?: CollaborationMessage[]
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

export interface ChatSession {
  id: string
  title: string
  created_at: string
  last_active_at: string
}

export interface ChatSessionListResponse {
  items: ChatSession[]
}

export interface ChatSessionMessagesResponse {
  items: ChatDetailResponse[]
  total: number
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
    sessionId?: string
    memoryPreferences?: { preferred_crafts: string[]; preferred_profile?: string | null }
    route?: WorkflowRoute
    workflowTrace?: WorkflowTraceEntry[]
    realtimeWorkflow?: RealtimeWorkflow
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
