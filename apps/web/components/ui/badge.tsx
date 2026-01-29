import * as React from "react";

import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "warning" | "destructive" | "info";

type BadgeProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: BadgeVariant;
};

const badgeStyles: Record<BadgeVariant, string> = {
  default:
    "border border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  success:
    "border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-600/40 dark:bg-emerald-900/30 dark:text-emerald-200",
  warning:
    "border border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-600/40 dark:bg-amber-900/30 dark:text-amber-200",
  destructive:
    "border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-600/40 dark:bg-rose-900/30 dark:text-rose-200",
  info: "border border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-600/40 dark:bg-sky-900/30 dark:text-sky-200"
};

const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = "default", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
          badgeStyles[variant],
          className
        )}
        {...props}
      />
    );
  }
);

Badge.displayName = "Badge";

export { Badge };
