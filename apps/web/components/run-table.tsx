"use client";

import type { KeyboardEvent } from "react";
import { useRouter } from "next/navigation";

import { RunStatusBadge } from "@/components/run-status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "@/components/ui/table";
import { formatCost, formatDuration } from "@/lib/run-utils";
import type { Run } from "@/lib/run-types";
import { cn } from "@/lib/utils";

type RunTableProps = {
  runs: Run[];
};

const RunTable = ({ runs }: RunTableProps) => {
  const router = useRouter();

  const handleRowClick = (runId: string) => {
    router.push(`/runs/${runId}`);
  };

  const handleRowKeyDown = (
    event: KeyboardEvent<HTMLTableRowElement>,
    runId: string
  ) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    handleRowClick(runId);
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Run ID</TableHead>
            <TableHead>Goal</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Cost</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => (
            <TableRow
              key={run.id}
              tabIndex={0}
              role="link"
              aria-label={`View run ${run.id}`}
              onClick={() => handleRowClick(run.id)}
              onKeyDown={(event) => handleRowKeyDown(event, run.id)}
              className={cn(
                "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
              )}
            >
              <TableCell className="font-mono text-xs text-slate-700 dark:text-slate-200">
                {run.id}
              </TableCell>
              <TableCell className="max-w-[420px] text-sm text-slate-700 dark:text-slate-200">
                <span className="block truncate">{run.goal}</span>
              </TableCell>
              <TableCell>
                <RunStatusBadge status={run.status} />
              </TableCell>
              <TableCell className="text-sm text-slate-600 dark:text-slate-300">
                {formatDuration(run.durationMs)}
              </TableCell>
              <TableCell className="text-sm text-slate-600 dark:text-slate-300">
                {formatCost(run.cost)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export { RunTable };
