import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { BudgetCard } from './shared/BudgetCard'
import { KpiCard } from './shared/KpiCard'
import { AddBudgetDialog } from './budget/AddBudgetDialog'
import { BudgetDetailPanel } from './budget/BudgetDetailPanel'
import { useBudgets } from '@/hooks/queries/useBudgets'
import type { BudgetType, BudgetConfig, RawJsonData } from '@/types/agentControl'

const budgetTypeOptions: { value: BudgetType | 'all'; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'global', label: 'Global' },
  { value: 'agent', label: 'Agent' },
  { value: 'customer', label: 'Customer' },
  { value: 'feature', label: 'Feature' },
  { value: 'tag', label: 'Tag' },
]

// Extract budgets from API response (handles policy-based structure)
function extractBudgets(data: RawJsonData | undefined): BudgetConfig[] {
  if (!data) return []
  if (Array.isArray(data)) return data as BudgetConfig[]
  if (data.policies && Array.isArray(data.policies)) {
    const allBudgets: BudgetConfig[] = []
    for (const policy of data.policies as Array<{ budgets?: BudgetConfig[] }>) {
      if (policy.budgets) allBudgets.push(...policy.budgets)
    }
    return allBudgets
  }
  if (data.budgets && Array.isArray(data.budgets)) {
    return data.budgets as BudgetConfig[]
  }
  return []
}

// Extract policyId from API response (uses first policy or 'default')
function extractPolicyId(data: RawJsonData | undefined): string | null {
  if (!data) return null
  if (data.policies && Array.isArray(data.policies) && data.policies.length > 0) {
    return (data.policies[0] as { id?: string }).id || 'default'
  }
  return 'default'
}

/**
 * Budget management panel with summary cards and budget list.
 */
export function CostControls() {
  const [typeFilter, setTypeFilter] = useState<BudgetType | 'all'>('all')
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [selectedBudget, setSelectedBudget] = useState<BudgetConfig | null>(null)
  const [detailPanelOpen, setDetailPanelOpen] = useState(false)

  const handleBudgetClick = (budget: BudgetConfig) => {
    setSelectedBudget(budget)
    setDetailPanelOpen(true)
  }

  const { data: rawData, isLoading, error } = useBudgets()

  // Parse budgets and policyId from API response
  const budgets = useMemo(
    () => extractBudgets(rawData as RawJsonData | undefined),
    [rawData]
  )

  const policyId = useMemo(
    () => extractPolicyId(rawData as RawJsonData | undefined),
    [rawData]
  )

  // Compute summary stats
  const summary = useMemo(() => {
    if (!budgets.length) return null
    return {
      totalBudget: budgets.reduce((sum: number, b: BudgetConfig) => sum + b.limit, 0),
      totalSpent: budgets.reduce((sum: number, b: BudgetConfig) => sum + b.spent, 0),
      activeAlerts: budgets.filter((b: BudgetConfig) =>
        b.alerts.some((a) => a.enabled && b.spent / b.limit >= a.threshold / 100)
      ).length,
      budgetsAtRisk: budgets.filter((b: BudgetConfig) => b.spent / b.limit >= 0.9).length,
    }
  }, [budgets])

  // Filter budgets by type
  const filteredBudgets = useMemo(
    () => budgets.filter((b: BudgetConfig) => typeFilter === 'all' || b.type === typeFilter),
    [budgets, typeFilter]
  )

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-red-500 mb-4">Failed to load budgets</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 pr-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Budget"
          value={summary ? formatCurrency(summary.totalBudget) : '-'}
          loading={isLoading}
          icon={
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path d="M4 4a2 2 0 00-2 2v4a2 2 0 002 2V6h10a2 2 0 00-2-2H4zm2 6a2 2 0 012-2h8a2 2 0 012 2v4a2 2 0 01-2 2H8a2 2 0 01-2-2v-4zm6 4a2 2 0 100-4 2 2 0 000 4z" />
            </svg>
          }
        />
        <KpiCard
          label="Total Spent"
          value={summary ? formatCurrency(summary.totalSpent) : '-'}
          loading={isLoading}
          trend={
            summary && summary.totalBudget > 0
              ? {
                  value: Math.round((summary.totalSpent / summary.totalBudget) * 100),
                  direction: summary.totalSpent / summary.totalBudget > 0.8 ? 'up' : 'down',
                }
              : undefined
          }
          icon={
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
        <KpiCard
          label="Active Alerts"
          value={summary?.activeAlerts ?? '-'}
          loading={isLoading}
          highlight={summary !== null && summary.activeAlerts > 0}
          icon={
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
            </svg>
          }
        />
        <KpiCard
          label="Budgets at Risk"
          value={summary?.budgetsAtRisk ?? '-'}
          loading={isLoading}
          highlight={summary !== null && summary.budgetsAtRisk > 0}
          icon={
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          }
        />
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Budgets</h2>
        <div className="flex items-center gap-3">
          <Select
            value={typeFilter}
            onValueChange={(value) => setTypeFilter(value as BudgetType | 'all')}
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              {budgetTypeOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => setAddDialogOpen(true)}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4 mr-2"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clipRule="evenodd"
              />
            </svg>
            Add Budget
          </Button>
        </div>
      </div>

      {/* Budget List */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-[72px]" />
          ))}
        </div>
      ) : filteredBudgets.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>No budgets found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredBudgets.map((budget: BudgetConfig) => (
            <BudgetCard
              key={budget.id}
              budget={budget}
              onClick={() => handleBudgetClick(budget)}
            />
          ))}
        </div>
      )}

      {/* Add Budget Dialog */}
      <AddBudgetDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        policyId={policyId}
      />

      {/* Budget Detail Panel */}
      <BudgetDetailPanel
        budget={selectedBudget}
        open={detailPanelOpen}
        onOpenChange={setDetailPanelOpen}
        policyId={policyId}
        existingBudgets={budgets}
      />
    </div>
  )
}
