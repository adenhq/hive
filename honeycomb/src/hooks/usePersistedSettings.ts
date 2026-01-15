/**
 * Persisted Settings Hooks
 *
 * Convenience hooks for consuming persisted UI settings.
 * These are drop-in replacements for local state in components.
 */

import { useCallback } from 'react'
import { useSettingsStore } from '@/stores/settingsStore'
import { useUpdateUISettings } from '@/hooks/queries/useSettings'
import type { TimeRange } from '@/types/settings'

// =============================================================================
// Sidebar Collapsed Hook
// =============================================================================

/**
 * Hook for sidebar collapsed state with persistence
 *
 * Drop-in replacement for:
 *   const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
 *
 * Usage:
 *   const { sidebarCollapsed, setSidebarCollapsed, toggleSidebar } = useSidebarCollapsed()
 */
export function useSidebarCollapsed() {
  const sidebarCollapsed = useSettingsStore((s) => s.sidebarCollapsed)
  const setSidebarCollapsedStore = useSettingsStore((s) => s.setSidebarCollapsed)
  const { debouncedUpdate } = useUpdateUISettings()

  const setSidebarCollapsed = useCallback(
    (collapsed: boolean) => {
      // Update store (and LocalStorage) immediately
      setSidebarCollapsedStore(collapsed)
      // Debounced sync to server
      debouncedUpdate({ sidebarCollapsed: collapsed })
    },
    [setSidebarCollapsedStore, debouncedUpdate]
  )

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed(!sidebarCollapsed)
  }, [sidebarCollapsed, setSidebarCollapsed])

  return {
    sidebarCollapsed,
    setSidebarCollapsed,
    toggleSidebar,
  }
}

// =============================================================================
// Time Range Hook
// =============================================================================

/**
 * Hook for performance dashboard time range with persistence
 *
 * Drop-in replacement for agentControlStore.timeRange usage:
 *   const timeRange = useAgentControlStore((state) => state.timeRange)
 *   const setTimeRange = useAgentControlStore((state) => state.setTimeRange)
 *
 * Usage:
 *   const { timeRange, setTimeRange } = usePersistedTimeRange()
 */
export function usePersistedTimeRange() {
  const timeRange = useSettingsStore((s) => s.performanceDashboardTimeRange)
  const setTimeRangeStore = useSettingsStore(
    (s) => s.setPerformanceDashboardTimeRange
  )
  const { debouncedUpdate } = useUpdateUISettings()

  const setTimeRange = useCallback(
    (range: TimeRange) => {
      // Update store (and LocalStorage) immediately
      setTimeRangeStore(range)
      // Debounced sync to server
      debouncedUpdate({ performanceDashboardTimeRange: range })
    },
    [setTimeRangeStore, debouncedUpdate]
  )

  return {
    timeRange,
    setTimeRange,
  }
}
