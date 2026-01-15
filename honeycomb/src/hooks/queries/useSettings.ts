/**
 * Settings Query Hooks
 *
 * React Query hooks for fetching and updating user UI settings.
 * Syncs server state to Zustand store for instant local access.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useCallback } from 'react'
import * as settingsApi from '@/services/settingsApi'
import { useSettingsStore } from '@/stores/settingsStore'
import type { UpdateUISettingsPayload } from '@/types/settings'

// Query key for settings
export const SETTINGS_QUERY_KEY = ['user', 'settings']

// =============================================================================
// Fetch Settings Hook
// =============================================================================

/**
 * Hook to fetch and sync UI settings from server
 *
 * - Fetches settings on mount
 * - Syncs server data to Zustand store (and LocalStorage)
 * - Falls back to defaults on error
 */
export function useUISettings() {
  const loadSettings = useSettingsStore((s) => s.loadSettings)

  const query = useQuery({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: async () => {
      const response = await settingsApi.getUISettings()
      return response.data
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1, // Don't retry too much - offline fallback is fine
  })

  // Sync server data to Zustand store
  useEffect(() => {
    if (query.data) {
      loadSettings(query.data)
    }
  }, [query.data, loadSettings])

  return query
}

// =============================================================================
// Update Settings Hook
// =============================================================================

/**
 * Hook to update UI settings with debouncing
 *
 * - Updates are optimistic (Zustand + LocalStorage first)
 * - Server sync is debounced (500ms) to prevent API spam
 * - Silent failures (settings still work via LocalStorage)
 */
export function useUpdateUISettings() {
  const queryClient = useQueryClient()
  const setIsSyncing = useSettingsStore((s) => s.setIsSyncing)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingUpdates = useRef<UpdateUISettingsPayload>({})

  const { mutate, ...mutationRest } = useMutation({
    mutationFn: (settings: UpdateUISettingsPayload) =>
      settingsApi.updateUISettings(settings),
    onMutate: () => {
      setIsSyncing(true)
    },
    onSuccess: (response) => {
      // Update query cache with server response
      queryClient.setQueryData(SETTINGS_QUERY_KEY, response.data)
    },
    onSettled: () => {
      setIsSyncing(false)
    },
    onError: (error) => {
      console.warn('[useUpdateUISettings] Failed to sync settings:', error)
      // Settings are already in LocalStorage, so offline works
    },
  })

  // Debounced update function
  // Note: mutate is referentially stable (unlike the mutation object itself)
  const debouncedUpdate = useCallback(
    (updates: UpdateUISettingsPayload) => {
      // Merge with pending updates
      pendingUpdates.current = { ...pendingUpdates.current, ...updates }

      // Clear existing timeout
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }

      // Set new debounce timeout (500ms)
      debounceRef.current = setTimeout(() => {
        const toSend = { ...pendingUpdates.current }
        pendingUpdates.current = {}
        mutate(toSend)
      }, 500)
    },
    [mutate]
  )

  // Cleanup on unmount - flush pending updates
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
        // Flush any pending updates
        if (Object.keys(pendingUpdates.current).length > 0) {
          mutate(pendingUpdates.current)
        }
      }
    }
  }, [mutate])

  return {
    mutate,
    ...mutationRest,
    debouncedUpdate,
  }
}
