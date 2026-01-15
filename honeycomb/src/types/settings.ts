/**
 * UI Settings Types
 *
 * Types for persisted user interface settings.
 * Settings are stored server-side (users.preferences) with LocalStorage cache.
 */

// TimeRange is also used by agentControlStore, keep it here as the source of truth
export type TimeRange = 'today' | 'week' | 'twoWeeks' | 'month' | 'all'

/**
 * User UI settings that persist across sessions and devices
 */
export interface UISettings {
  sidebarCollapsed: boolean
  performanceDashboardTimeRange: TimeRange
}

/**
 * Default settings for new users or offline fallback
 */
export const DEFAULT_UI_SETTINGS: UISettings = {
  sidebarCollapsed: false,
  performanceDashboardTimeRange: 'today',
}

/**
 * API response shape for settings endpoints
 */
export interface UISettingsResponse {
  success: boolean
  data: UISettings
}

/**
 * Update payload - supports partial updates
 */
export type UpdateUISettingsPayload = Partial<UISettings>
