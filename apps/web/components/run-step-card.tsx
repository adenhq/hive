"use client";

import { RunStatusBadge } from "@/components/run-status-badge";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { formatDateTime, formatDuration } from "@/lib/run-utils";
import type { RunStep } from "@/lib/run-types";
import { cn } from "@/lib/utils";

type RunStepCardProps = {
  step: RunStep;
  index: number;
};

const getStepDurationMs = (step: RunStep): number | undefined => {
  if (!step.startedAt || !step.endedAt) {
    return undefined;
  }

  const startedTime = Date.parse(step.startedAt);
  const endedTime = Date.parse(step.endedAt);

  if (Number.isNaN(startedTime) || Number.isNaN(endedTime)) {
    return undefined;
  }

  return Math.max(endedTime - startedTime, 0);
};

const stringifyPayload = (payload: unknown): string => {
  if (payload === undefined) {
    return "";
  }

  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
};

const RunStepCard = ({ step, index }: RunStepCardProps) => {
  const isFailed = step.status === "failed";
  const hasInput = step.input !== undefined;
  const hasOutput = step.output !== undefined;
  const hasError = Boolean(step.error);
  const duration = formatDuration(getStepDurationMs(step));

  return (
    <Card
      className={cn(
        "border-slate-200 dark:border-slate-800",
        isFailed &&
          "border-rose-200 bg-rose-50/40 dark:border-rose-700/60 dark:bg-rose-950/30"
      )}
    >
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Step {index + 1}: {step.nodeName}
            </CardTitle>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Retries: {step.retries}
            </p>
          </div>
          <RunStatusBadge status={step.status} />
        </div>
        <div className="flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400">
          <span>Started: {formatDateTime(step.startedAt)}</span>
          <span>Ended: {formatDateTime(step.endedAt)}</span>
          <span>Duration: {duration}</span>
        </div>
      </CardHeader>
      <Separator />
      <CardContent className="space-y-3 pt-4">
        {!hasInput && !hasOutput && !hasError ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No payloads recorded for this step.
          </p>
        ) : (
          <Accordion type="multiple" className="w-full">
            {hasInput && (
              <AccordionItem value={`input-${step.id}`}>
                <AccordionTrigger>Input</AccordionTrigger>
                <AccordionContent>
                  <ScrollArea className="max-h-56 w-full rounded-md border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
                    <pre className="p-3 text-xs text-slate-700 dark:text-slate-200">
                      {stringifyPayload(step.input)}
                    </pre>
                  </ScrollArea>
                </AccordionContent>
              </AccordionItem>
            )}
            {hasOutput && (
              <AccordionItem value={`output-${step.id}`}>
                <AccordionTrigger>Output</AccordionTrigger>
                <AccordionContent>
                  <ScrollArea className="max-h-56 w-full rounded-md border border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
                    <pre className="p-3 text-xs text-slate-700 dark:text-slate-200">
                      {stringifyPayload(step.output)}
                    </pre>
                  </ScrollArea>
                </AccordionContent>
              </AccordionItem>
            )}
            {hasError && (
              <AccordionItem value={`error-${step.id}`}>
                <AccordionTrigger>Error</AccordionTrigger>
                <AccordionContent>
                  <div className="rounded-md border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 dark:border-rose-700/60 dark:bg-rose-950/40 dark:text-rose-200">
                    {step.error}
                  </div>
                </AccordionContent>
              </AccordionItem>
            )}
          </Accordion>
        )}
      </CardContent>
    </Card>
  );
};

export { RunStepCard };
