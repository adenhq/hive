import { create } from 'zustand'
import type { LLMEvent, AgentStatus } from '@/types/agentControl'

// =============================================================================
// Types
// =============================================================================

export type TimeRange = 'today' | 'week' | 'twoWeeks' | 'month' | 'all'

const MAX_EVENTS_BUFFER = 1000

interface AgentControlState {
  // Time range selection for analytics
  timeRange: TimeRange
  setTimeRange: (range: TimeRange) => void

  // Selection state for detail views
  selectedBudgetId: string | null
  setSelectedBudgetId: (id: string | null) => void
  selectedAgentId: string | null
  setSelectedAgentId: (id: string | null) => void

  // Real-time events buffer from WebSocket
  eventsBuffer: LLMEvent[]
  addEvents: (events: LLMEvent[]) => void
  clearEvents: () => void

  // Agent status from WebSocket
  agentStatus: AgentStatus | null
  setAgentStatus: (status: AgentStatus) => void
}

// =============================================================================
// Store
// =============================================================================

export const useAgentControlStore = create<AgentControlState>((set) => ({
  // Time range - default to today
  timeRange: 'today',
  setTimeRange: (range) => set({ timeRange: range }),

  // Budget selection
  selectedBudgetId: null,
  setSelectedBudgetId: (id) => set({ selectedBudgetId: id }),

  // Agent selection
  selectedAgentId: null,
  setSelectedAgentId: (id) => set({ selectedAgentId: id }),

  // Events buffer for real-time updates
  eventsBuffer: [],
  addEvents: (events) =>
    set((state) => {
      // More efficient: concat instead of spread, only slice if necessary
      const combined = events.concat(state.eventsBuffer)
      if (combined.length <= MAX_EVENTS_BUFFER) {
        return { eventsBuffer: combined }
      }
      return { eventsBuffer: combined.slice(0, MAX_EVENTS_BUFFER) }
    }),
  clearEvents: () => set({ eventsBuffer: [] }),

  // Agent status from WebSocket
  agentStatus: null,
  setAgentStatus: (status) => set({ agentStatus: status }),
}))
