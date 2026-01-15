import { useState, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { LiveIndicator } from './shared/LiveIndicator'
import { DateRangePicker } from '@/components/ui/date-range-picker'
import { useLogs, useLogsAggregated } from '@/hooks/queries/useLogs'
import { useAgentControlStore } from '@/stores/agentControlStore'
import type { DateRange } from 'react-day-picker'

type ViewType = 'raw' | 'metrics' | 'model' | 'agent'
type LogType = 'llm_request' | 'tool_call' | 'error'

const viewOptions = [
  { value: 'raw', label: 'Raw Data' },
  { value: 'metrics', label: 'Metrics Summary' },
  { value: 'model', label: 'Model Usage' },
  { value: 'agent', label: 'Agent Activity' },
]

interface LogEntry {
  id?: string
  timestamp: string
  derived_type: LogType
  derived_success: boolean
  agent?: string
  model?: string
  provider?: string
  cost_total?: number
  latency_ms?: number
  finish_reason?: string
  tool_call_count?: number
  usage_input_tokens?: number
  usage_output_tokens?: number
  usage_total_tokens?: number
  [key: string]: unknown
}

interface AggregatedEntry {
  model?: string
  agent?: string
  request_count: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_cost: number
  avg_latency_ms: number
  first_seen?: string
  last_seen?: string
}

export function DataPanel() {
  const [viewType, setViewType] = useState<ViewType>('raw')
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  // Default date range: last 7 days
  const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
    const end = new Date()
    end.setHours(23, 59, 59, 999)
    const start = new Date()
    start.setDate(start.getDate() - 7)
    start.setHours(0, 0, 0, 0)
    return { from: start, to: end }
  })

  const hasActiveAgents = useAgentControlStore((state) => state.eventsBuffer.length > 0)

  // Convert date range to ISO strings for API
  const startDate = useMemo(() => {
    return dateRange?.from?.toISOString() ?? new Date().toISOString()
  }, [dateRange?.from])

  const endDate = useMemo(() => {
    return dateRange?.to?.toISOString() ?? new Date().toISOString()
  }, [dateRange?.to])

  // Fetch raw logs for 'raw' and 'metrics' views
  const {
    data: logsData,
    isLoading: logsLoading,
    error: logsError,
    refetch: refetchLogs,
  } = useLogs(startDate, endDate, 500, viewType === 'raw' || viewType === 'metrics')

  // Fetch aggregated data for 'model' view
  const {
    data: modelData,
    isLoading: modelLoading,
    error: modelError,
    refetch: refetchModel,
  } = useLogsAggregated(startDate, endDate, 'model', 100, viewType === 'model')

  // Fetch aggregated data for 'agent' view
  const {
    data: agentData,
    isLoading: agentLoading,
    error: agentError,
    refetch: refetchAgent,
  } = useLogsAggregated(startDate, endDate, 'agent', 100, viewType === 'agent')

  // Parse logs from API response
  const logs = useMemo((): LogEntry[] => {
    if (!logsData) return []
    const rawLogs = (logsData as { rows?: unknown[] }).rows ||
                    (logsData as { logs?: unknown[] }).logs ||
                    (Array.isArray(logsData) ? logsData : [])
    return (rawLogs as LogEntry[]).map((log, idx) => ({
      ...log,
      id: log.id || `log-${idx}`,
    }))
  }, [logsData])

  // Parse aggregated data
  const modelAggregations = useMemo((): AggregatedEntry[] => {
    if (!modelData) return []
    return (modelData as { aggregations?: AggregatedEntry[] }).aggregations || []
  }, [modelData])

  const agentAggregations = useMemo((): AggregatedEntry[] => {
    if (!agentData) return []
    return (agentData as { aggregations?: AggregatedEntry[] }).aggregations || []
  }, [agentData])

  // Determine loading/error state based on current view
  const isLoading = viewType === 'raw' || viewType === 'metrics'
    ? logsLoading
    : viewType === 'model'
    ? modelLoading
    : agentLoading

  const error = viewType === 'raw' || viewType === 'metrics'
    ? logsError
    : viewType === 'model'
    ? modelError
    : agentError

  const refetch = viewType === 'raw' || viewType === 'metrics'
    ? refetchLogs
    : viewType === 'model'
    ? refetchModel
    : refetchAgent

  const handleExport = () => {
    let csv = ''

    if (viewType === 'raw') {
      if (!logs.length) return
      csv = [
        ['Timestamp', 'Provider', 'Model', 'Agent', 'Tokens', 'Cost', 'Latency'].join(','),
        ...logs.map((log) =>
          [
            log.timestamp,
            log.provider || '-',
            log.model || '-',
            log.agent || '-',
            log.usage_total_tokens ?? '-',
            log.cost_total ? Number(log.cost_total).toFixed(6) : '-',
            log.latency_ms ? `${Math.round(Number(log.latency_ms))}ms` : '-',
          ].join(',')
        ),
      ].join('\n')
    } else if (viewType === 'metrics') {
      const successCount = logs.filter((l) => l.derived_success).length
      const totalCost = logs.reduce((sum, l) => sum + (Number(l.cost_total) || 0), 0)
      csv = [
        ['Metric', 'Value'].join(','),
        ['Total Requests', logs.length].join(','),
        ['Success Rate', `${((successCount / Math.max(logs.length, 1)) * 100).toFixed(1)}%`].join(','),
        ['Total Cost', `$${totalCost.toFixed(2)}`].join(','),
      ].join('\n')
    } else if (viewType === 'model') {
      if (!modelAggregations.length) return
      csv = [
        ['Model', 'Requests', 'Input Tokens', 'Output Tokens', 'Total Cost', 'Avg Latency'].join(','),
        ...modelAggregations.map((row) =>
          [
            row.model || '-',
            row.request_count,
            row.total_input_tokens,
            row.total_output_tokens,
            `$${row.total_cost.toFixed(4)}`,
            `${Math.round(row.avg_latency_ms)}ms`,
          ].join(',')
        ),
      ].join('\n')
    } else if (viewType === 'agent') {
      if (!agentAggregations.length) return
      csv = [
        ['Agent', 'Requests', 'Input Tokens', 'Output Tokens', 'Total Cost', 'Avg Latency'].join(','),
        ...agentAggregations.map((row) =>
          [
            row.agent || '-',
            row.request_count,
            row.total_input_tokens,
            row.total_output_tokens,
            `$${row.total_cost.toFixed(4)}`,
            `${Math.round(row.avg_latency_ms)}ms`,
          ].join(',')
        ),
      ].join('\n')
    }

    if (!csv) return

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs-${viewType}-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatTimestamp = (ts: string) => {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const getCardTitle = () => {
    switch (viewType) {
      case 'raw':
        return 'Raw Data'
      case 'metrics':
        return 'Metrics Summary'
      case 'model':
        return 'Model Usage'
      case 'agent':
        return 'Agent Activity'
      default:
        return 'Data'
    }
  }

  const hasData = () => {
    switch (viewType) {
      case 'raw':
      case 'metrics':
        return logs.length > 0
      case 'model':
        return modelAggregations.length > 0
      case 'agent':
        return agentAggregations.length > 0
      default:
        return false
    }
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-red-500 mb-4">Failed to load data</p>
        <Button variant="outline" onClick={() => refetch()}>
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6 pr-6">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <DateRangePicker value={dateRange} onChange={setDateRange} />

          <Select value={viewType} onValueChange={(v) => setViewType(v as ViewType)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select view" />
            </SelectTrigger>
            <SelectContent>
              {viewOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-3">
          <LiveIndicator isLive={hasActiveAgents} />
          <Button variant="outline" onClick={handleExport} disabled={!hasData()}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4 mr-2"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
            Export CSV
          </Button>
        </div>
      </div>

      {/* Data Table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>{getCardTitle()}</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(10)].map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : !hasData() ? (
            <div className="text-center py-12 text-muted-foreground">
              No data found for the selected date range
            </div>
          ) : viewType === 'raw' ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead className="text-right">Tokens</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                  <TableHead className="text-right">Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <>
                    <TableRow
                      key={log.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() =>
                        setExpandedRow(expandedRow === log.id ? null : log.id || null)
                      }
                    >
                      <TableCell className="font-mono text-xs">
                        {formatTimestamp(log.timestamp)}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {log.provider || '-'}
                        </Badge>
                      </TableCell>
                      <TableCell className="truncate max-w-[150px]">
                        {log.model || '-'}
                      </TableCell>
                      <TableCell className="truncate max-w-[150px]">
                        {log.agent || '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {log.usage_total_tokens ?? '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {log.cost_total ? `$${Number(log.cost_total).toFixed(6)}` : '-'}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {log.latency_ms ? `${Math.round(Number(log.latency_ms))}ms` : '-'}
                      </TableCell>
                    </TableRow>
                    {expandedRow === log.id && (
                      <TableRow>
                        <TableCell colSpan={7} className="bg-muted/30">
                          <pre className="text-xs p-4 overflow-auto max-h-[300px]">
                            {JSON.stringify(log, null, 2)}
                          </pre>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                ))}
              </TableBody>
            </Table>
          ) : viewType === 'metrics' ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead>Value</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">Total Requests</TableCell>
                  <TableCell>{logs.length}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Success Rate</TableCell>
                  <TableCell>
                    {(
                      (logs.filter((l) => l.derived_success).length /
                        Math.max(logs.length, 1)) *
                      100
                    ).toFixed(1)}
                    %
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Total Cost</TableCell>
                  <TableCell>
                    $
                    {logs
                      .reduce((sum, l) => sum + (Number(l.cost_total) || 0), 0)
                      .toFixed(2)}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Total Tokens</TableCell>
                  <TableCell>
                    {logs
                      .reduce((sum, l) => sum + (Number(l.usage_total_tokens) || 0), 0)
                      .toLocaleString()}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Avg Latency</TableCell>
                  <TableCell>
                    {Math.round(
                      logs.reduce((sum, l) => sum + (Number(l.latency_ms) || 0), 0) /
                        Math.max(logs.length, 1)
                    )}
                    ms
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          ) : viewType === 'model' ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead className="text-right">Requests</TableHead>
                  <TableHead className="text-right">Input Tokens</TableHead>
                  <TableHead className="text-right">Output Tokens</TableHead>
                  <TableHead className="text-right">Total Cost</TableHead>
                  <TableHead className="text-right">Avg Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {modelAggregations.map((row, idx) => (
                  <TableRow key={row.model || idx}>
                    <TableCell className="font-medium">{row.model || '-'}</TableCell>
                    <TableCell className="text-right">{row.request_count}</TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {row.total_input_tokens.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {row.total_output_tokens.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      ${row.total_cost.toFixed(4)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {Math.round(row.avg_latency_ms)}ms
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : viewType === 'agent' ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead className="text-right">Requests</TableHead>
                  <TableHead className="text-right">Input Tokens</TableHead>
                  <TableHead className="text-right">Output Tokens</TableHead>
                  <TableHead className="text-right">Total Cost</TableHead>
                  <TableHead className="text-right">Avg Latency</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {agentAggregations.map((row, idx) => (
                  <TableRow key={row.agent || idx}>
                    <TableCell className="font-medium">{row.agent || '(no agent)'}</TableCell>
                    <TableCell className="text-right">{row.request_count}</TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {row.total_input_tokens.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {row.total_output_tokens.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      ${row.total_cost.toFixed(4)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {Math.round(row.avg_latency_ms)}ms
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
