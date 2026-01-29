"use client";

import type { KeyboardEvent } from "react";

import { cn } from "@/lib/utils";

type RunIdCopyButtonProps = {
  runId: string;
  className?: string;
};

const RunIdCopyButton = ({ runId, className }: RunIdCopyButtonProps) => {
  const handleCopyClick = () => {
    if (!navigator?.clipboard?.writeText) {
      return;
    }

    void navigator.clipboard.writeText(runId);
  };

  const handleCopyKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    handleCopyClick();
  };

  return (
    <button
      type="button"
      aria-label="Copy run id"
      onClick={handleCopyClick}
      onKeyDown={handleCopyKeyDown}
      className={cn(
        "inline-flex items-center rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800",
        className
      )}
    >
      Copy ID
    </button>
  );
};

export { RunIdCopyButton };
