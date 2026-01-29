import { Badge } from "@/components/ui/badge";
import type { RunStatus, RunStepStatus } from "@/lib/run-types";
import { cn } from "@/lib/utils";

type StatusValue = RunStatus | RunStepStatus;

type StatusConfig = {
  label: string;
  variant: "default" | "success" | "warning" | "destructive" | "info";
};

const statusConfigMap: Record<StatusValue, StatusConfig> = {
  running: { label: "Running", variant: "info" },
  success: { label: "Success", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  evolved: { label: "Evolved", variant: "warning" },
  pending: { label: "Pending", variant: "default" }
};

type RunStatusBadgeProps = {
  status: StatusValue;
  className?: string;
};

const RunStatusBadge = ({ status, className }: RunStatusBadgeProps) => {
  const config = statusConfigMap[status] ?? statusConfigMap.pending;

  return (
    <Badge variant={config.variant} className={cn("whitespace-nowrap", className)}>
      {config.label}
    </Badge>
  );
};

export { RunStatusBadge };
