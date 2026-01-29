export type RunStatus = "running" | "success" | "failed" | "evolved";

export type RunStepStatus = "pending" | "running" | "success" | "failed";

export type RunStep = {
  id: string;
  nodeName: string;
  status: RunStepStatus;
  retries: number;
  input?: unknown;
  output?: unknown;
  error?: string;
  startedAt?: string;
  endedAt?: string;
};

export type Run = {
  id: string;
  goal: string;
  status: RunStatus;
  startedAt: string;
  endedAt?: string;
  durationMs?: number;
  cost?: number;
  steps: RunStep[];
};
