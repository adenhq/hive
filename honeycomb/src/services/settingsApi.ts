/**
 * Settings API Service
 *
 * API client methods for user UI settings.
 */

import { serverClient } from './api'
import type { UISettingsResponse, UpdateUISettingsPayload } from '@/types/settings'

/**
 * Get user UI settings from server
 */
export function getUISettings(): Promise<UISettingsResponse> {
  return serverClient.get<UISettingsResponse>('/user/settings')
}

/**
 * Update user UI settings on server
 * Supports partial updates - only send changed fields
 */
export function updateUISettings(
  settings: UpdateUISettingsPayload
): Promise<UISettingsResponse> {
  return serverClient.put<UISettingsResponse>('/user/settings', settings)
}
