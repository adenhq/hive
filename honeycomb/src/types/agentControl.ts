// =============================================================================
// KPI & Analytics Types
// =============================================================================

export interface KPIValues {
  totalCost: number
  projectedMonthlyCost: number
  totalRequests: number
  totalTokens: number
  successRate: number
  avgLatency: number
  cacheSavings: number
}

export interface UsagePattern {
  title: string
  description: string
  icon: string
  iconBg: string
  stats: Array<{ label: string; value: string }>
}

export interface MetricsSummaryData {
  metricName: string
  value: string
  unit: string
  period: string
  trend: 'up' | 'down' | 'neutral'
  trendValue: string
}

export interface CostTrendData {
  date: string
  cost: number
  requests: number
  budget?: number
}

export interface TokenUsageData {
  date: string
  input: number
  output: number
}

export interface LatencyPercentilesData {
  date: string
  p50: number
  p95: number
  p99: number
}

export interface LatencyData {
  range: string
  count: number
}

export interface CostEfficiencyData {
  date: string
  costPerSuccess: number
  successRate: number
}

export interface BurnRateData {
  monthlyBudget: number
  currentSpend: number
  daysElapsed: number
  daysInMonth: number
  projectedSpend: number
  burnRate: number
  avgDailySpend: number
  daysUntilExhaustion: number
}

export interface CostByModelData {
  name: string
  value: number
  cost: number
  color: string
}

export interface TopAgentData {
  name: string
  spend: number
  requests: number
  avgCost: number
  limit?: number
}

export interface ModelUsageData {
  model: string
  provider?: string
  requests: number
  tokens: number
  avgLatency: number
  totalCost: number
}

export interface AgentActivityData {
  agent: string
  lastActive: string
  totalRequests: number
  totalTokens?: number
  totalCost?: number
  avgLatency?: number
}

// =============================================================================
// Budget Management Types
// =============================================================================

export type BudgetType = 'global' | 'agent' | 'customer' | 'feature' | 'tag'
export type LimitAction = 'kill' | 'throttle' | 'degrade' | 'notify'

export interface BudgetAlert {
  threshold: number
  enabled: boolean
}

export interface BudgetNotifications {
  inApp: boolean
  email: boolean
  emailRecipients: string[]
  webhook: boolean
}

export interface BudgetConfig {
  id: string
  name: string
  type: BudgetType
  tagCategory?: string
  tags?: string[]
  limit: number
  spent: number
  limitAction: LimitAction
  degradeToModel?: string
  throttleRate?: number
  alerts: BudgetAlert[]
  notifications: BudgetNotifications
}

export interface BudgetSummary {
  totalBudget: number
  totalSpent: number
  activeAlerts: number
  budgetsAtRisk: number
}

// =============================================================================
// Conversation & Tool Types
// =============================================================================

export interface ConversationData {
  id: string
  turns: number
  tokens: string
  cost: string
  latency: string
  cacheEfficiency: number
}

export interface ContextGrowthData {
  turn: number
  tokens: number
}

export interface ToolUsageData {
  name: string
  count: number
}

// =============================================================================
// Insights Types
// =============================================================================

export type InsightCategory = 'cost' | 'performance' | 'reliability' | 'efficiency'
export type InsightSeverity = 'critical' | 'warning' | 'info' | 'positive'

export interface Insight {
  id: string
  title: string
  description: string
  category: InsightCategory
  severity: InsightSeverity
  action: string
  metric?: Record<string, unknown>
}

// =============================================================================
// Chat & Session Types
// =============================================================================

export interface SessionSummary {
  sessionId: string
  sessionName: string
  createdAt: string
  lastActivity: string
  messageCount: number
}

export interface PaginatedSessions {
  sessions: SessionSummary[]
  totalCount: number
  page: number
  size: number
  totalPages: number
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: string
  // Tool-related fields (present when role === 'tool')
  type?: 'tool_call' | 'tool_result'
  toolCallId?: string
  toolName?: string
  toolArgs?: Record<string, unknown>
  success?: boolean
}

// =============================================================================
// Agent Status Types
// =============================================================================

export interface AgentStatusInstance {
  instance_id: string
  policy_id: string | null
  connected_at: string
  last_heartbeat: string
}

export interface AgentStatus {
  active: boolean
  count: number
  instances: AgentStatusInstance[]
  timestamp: string
  error?: string
}

export interface AgentInfo {
  agent: string
  agent_name: string | null
  status: 'connected' | 'disconnected'
  connection_type: 'websocket' | 'http' | null
  instance_id: string | null
  first_seen: string
  last_seen: string
  total_requests: number
  total_cost: number
}

export interface AgentsResponse {
  agents: AgentInfo[]
  total: number
  connected_count: number
  timestamp: string
}

// =============================================================================
// Real-time Event Types (WebSocket)
// =============================================================================

export interface LLMEvent {
  timestamp: string
  agent: string
  model: string
  inputTokens: number
  outputTokens: number
  cost: number
  latency: number
  success: boolean
}

export interface LLMEventsBatch {
  events: LLMEvent[]
  timestamp: string
}

export interface PolicyUpdate {
  policyId: string
  budgetId?: string
  action: 'created' | 'updated' | 'deleted'
  data?: BudgetConfig
}

// =============================================================================
// API Response Types
// =============================================================================

export type RawJsonData = Record<string, unknown>

export interface CreateSessionResponse {
  sessionId: string
  sessionName: string
  createdAt: string
}

export interface SessionHistoryResponse {
  messages: ChatMessage[]
}

export interface SuccessResponse {
  success: boolean
}
