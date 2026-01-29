import { RunStepCard } from "@/components/run-step-card";
import type { RunStep, RunStepStatus } from "@/lib/run-types";
import { cn } from "@/lib/utils";

type RunTimelineProps = {
  steps: RunStep[];
};

const statusDotStyles: Record<RunStepStatus, string> = {
  pending: "bg-slate-400",
  running: "bg-sky-500",
  success: "bg-emerald-500",
  failed: "bg-rose-500"
};

const RunTimeline = ({ steps }: RunTimelineProps) => {
  if (steps.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
        No steps have been recorded for this run yet.
      </div>
    );
  }

  return (
    <ol className="border-l border-slate-200 dark:border-slate-800">
      {steps.map((step, index) => (
        <li key={step.id} className="relative ml-6 pb-6 last:pb-0">
          <span
            className={cn(
              "absolute -left-[7px] mt-2 h-3.5 w-3.5 rounded-full ring-4 ring-slate-50 dark:ring-slate-950",
              statusDotStyles[step.status]
            )}
          />
          <RunStepCard step={step} index={index} />
        </li>
      ))}
    </ol>
  );
};

export { RunTimeline };
