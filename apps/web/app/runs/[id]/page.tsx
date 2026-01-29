import { notFound } from "next/navigation";

import { RunIdCopyButton } from "@/components/run-id-copy-button";
import { RunStatusBadge } from "@/components/run-status-badge";
import { RunTimeline } from "@/components/run-timeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getMockRunById } from "@/lib/data-adapter";
import { formatCost, formatDateTime, formatDuration } from "@/lib/run-utils";

type RunDetailPageProps = {
  params: {
    id: string;
  };
};

const RunDetailPage = ({ params }: RunDetailPageProps) => {
  const run = getMockRunById(params.id);

  if (!run) {
    notFound();
  }

  return (
    <main className="flex flex-col gap-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Run detail
          </p>
          <RunStatusBadge status={run.status} />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
            {run.id}
          </h1>
          <RunIdCopyButton runId={run.id} />
        </div>
        <p className="max-w-3xl text-sm text-slate-600 dark:text-slate-300">
          {run.goal}
        </p>
      </header>

      <Separator />

      <section className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Timing</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            <div className="flex items-center justify-between">
              <span>Started</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {formatDateTime(run.startedAt)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Ended</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {formatDateTime(run.endedAt)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Duration</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {formatDuration(run.durationMs)}
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Cost</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            <div className="flex items-center justify-between">
              <span>Total</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {formatCost(run.cost)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Steps</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {run.steps.length}
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
            <div className="flex items-center justify-between">
              <span>State</span>
              <RunStatusBadge status={run.status} />
            </div>
            <div className="flex items-center justify-between">
              <span>Failures</span>
              <span className="font-medium text-slate-900 dark:text-slate-100">
                {run.steps.filter((step) => step.status === "failed").length}
              </span>
            </div>
          </CardContent>
        </Card>
      </section>

      <Separator />

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Execution timeline
          </h2>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {run.steps.length} steps
          </span>
        </div>
        <RunTimeline steps={run.steps} />
      </section>
    </main>
  );
};

export default RunDetailPage;
