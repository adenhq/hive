import type { Run, RunStatus, RunStep, RunStepStatus } from "@/lib/run-types";

const runStatuses: RunStatus[] = ["running", "success", "failed", "evolved"];
const stepStatuses: RunStepStatus[] = [
  "pending",
  "running",
  "success",
  "failed"
];

const toStringValue = (value: unknown, fallback = ""): string => {
  return typeof value === "string" ? value : fallback;
};

const toOptionalStringValue = (value: unknown): string | undefined => {
  return typeof value === "string" ? value : undefined;
};

const toNumberValue = (value: unknown): number | undefined => {
  if (typeof value !== "number") {
    return undefined;
  }

  if (Number.isNaN(value)) {
    return undefined;
  }

  return value;
};

const toRunStatus = (value: unknown): RunStatus => {
  if (typeof value === "string" && runStatuses.includes(value as RunStatus)) {
    return value as RunStatus;
  }

  return "running";
};

const toStepStatus = (value: unknown): RunStepStatus => {
  if (typeof value === "string" && stepStatuses.includes(value as RunStepStatus)) {
    return value as RunStepStatus;
  }

  return "pending";
};

const computeDurationMs = (
  startedAt?: string,
  endedAt?: string,
  durationMs?: number
): number | undefined => {
  if (typeof durationMs === "number") {
    return durationMs;
  }

  if (!startedAt || !endedAt) {
    return undefined;
  }

  const startedTime = Date.parse(startedAt);
  const endedTime = Date.parse(endedAt);

  if (Number.isNaN(startedTime) || Number.isNaN(endedTime)) {
    return undefined;
  }

  return Math.max(endedTime - startedTime, 0);
};

const mapHiveRunStepToUIRunStep = (raw: Record<string, unknown>): RunStep => {
  return {
    id: toStringValue(raw.id ?? raw.step_id ?? raw.uuid, "step-unknown"),
    nodeName: toStringValue(raw.nodeName ?? raw.node_name ?? raw.node, "unknown"),
    status: toStepStatus(raw.status),
    retries: toNumberValue(raw.retries) ?? 0,
    input: raw.input,
    output: raw.output,
    error: toOptionalStringValue(raw.error),
    startedAt: toOptionalStringValue(raw.startedAt ?? raw.started_at),
    endedAt: toOptionalStringValue(raw.endedAt ?? raw.ended_at)
  };
};

export const mapHiveRunToUIRun = (raw: Record<string, unknown>): Run => {
  const startedAt = toStringValue(raw.startedAt ?? raw.started_at, "");
  const endedAt = toOptionalStringValue(raw.endedAt ?? raw.ended_at);
  const durationMs = computeDurationMs(
    startedAt,
    endedAt,
    toNumberValue(raw.durationMs ?? raw.duration_ms)
  );

  const rawSteps = Array.isArray(raw.steps) ? raw.steps : [];

  return {
    id: toStringValue(raw.id ?? raw.run_id ?? raw.uuid, "run-unknown"),
    goal: toStringValue(raw.goal ?? raw.objective ?? raw.description, "Untitled"),
    status: toRunStatus(raw.status),
    startedAt,
    endedAt,
    durationMs,
    cost: toNumberValue(raw.cost ?? raw.cost_usd),
    steps: rawSteps.map((step) =>
      mapHiveRunStepToUIRunStep(step as Record<string, unknown>)
    )
  };
};

const mockHiveRuns: Record<string, unknown>[] = [
  {
    run_id: "run-2026-01-29-001",
    goal: "Summarize the latest architecture changes and notify the team.",
    status: "success",
    started_at: "2026-01-29T09:12:04Z",
    ended_at: "2026-01-29T09:14:38Z",
    cost_usd: 0.48,
    steps: [
      {
        step_id: "step-1",
        node_name: "planner",
        status: "success",
        retries: 0,
        input: {
          context: "Release notes and architectural changelog"
        },
        output: {
          plan: ["Review changes", "Draft summary", "Notify team"]
        },
        started_at: "2026-01-29T09:12:04Z",
        ended_at: "2026-01-29T09:12:14Z"
      },
      {
        step_id: "step-2",
        node_name: "summarizer",
        status: "success",
        retries: 0,
        input: {
          documents: ["architecture.md", "changelog.md"]
        },
        output: {
          summary:
            "Key changes include updated runtime hooks and improved trace metadata."
        },
        started_at: "2026-01-29T09:12:14Z",
        ended_at: "2026-01-29T09:13:41Z"
      },
      {
        step_id: "step-3",
        node_name: "notifier",
        status: "success",
        retries: 1,
        input: {
          channel: "#eng-updates"
        },
        output: {
          messageId: "slack-8273"
        },
        started_at: "2026-01-29T09:13:41Z",
        ended_at: "2026-01-29T09:14:38Z"
      }
    ]
  },
  {
    run_id: "run-2026-01-29-002",
    goal: "Evaluate pull request risk and open a review summary.",
    status: "failed",
    started_at: "2026-01-29T10:20:11Z",
    ended_at: "2026-01-29T10:25:07Z",
    cost_usd: 0.62,
    steps: [
      {
        step_id: "step-1",
        node_name: "context-loader",
        status: "success",
        retries: 0,
        input: {
          repo: "adenhq/hive",
          pr: 128
        },
        output: {
          filesChanged: 12
        },
        started_at: "2026-01-29T10:20:11Z",
        ended_at: "2026-01-29T10:21:02Z"
      },
      {
        step_id: "step-2",
        node_name: "risk-analyzer",
        status: "failed",
        retries: 2,
        input: {
          signals: ["security", "perf", "test-coverage"]
        },
        error: "Timeout while scoring dependency graph.",
        started_at: "2026-01-29T10:21:02Z",
        ended_at: "2026-01-29T10:24:49Z"
      },
      {
        step_id: "step-3",
        node_name: "summary-writer",
        status: "pending",
        retries: 0,
        input: {
          format: "markdown"
        }
      }
    ]
  },
  {
    run_id: "run-2026-01-29-003",
    goal: "Evolve the agent planning prompt for better decomposition.",
    status: "evolved",
    started_at: "2026-01-29T11:02:55Z",
    ended_at: "2026-01-29T11:09:12Z",
    cost_usd: 0.91,
    steps: [
      {
        step_id: "step-1",
        node_name: "prompt-review",
        status: "success",
        retries: 0,
        input: {
          prompt: "Current planner prompt"
        },
        output: {
          findings: ["Missing edge-case handling", "Long steps"]
        },
        started_at: "2026-01-29T11:02:55Z",
        ended_at: "2026-01-29T11:05:02Z"
      },
      {
        step_id: "step-2",
        node_name: "prompt-writer",
        status: "success",
        retries: 1,
        input: {
          goal: "Improve decomposition"
        },
        output: {
          updatedPrompt: "..."
        },
        started_at: "2026-01-29T11:05:02Z",
        ended_at: "2026-01-29T11:07:48Z"
      },
      {
        step_id: "step-3",
        node_name: "validator",
        status: "success",
        retries: 0,
        input: {
          checks: ["lint", "smoke"]
        },
        output: {
          result: "approved"
        },
        started_at: "2026-01-29T11:07:48Z",
        ended_at: "2026-01-29T11:09:12Z"
      }
    ]
  }
];

export const getMockRuns = (): Run[] => {
  return mockHiveRuns.map((run) => mapHiveRunToUIRun(run));
};

export const getMockRunById = (runId: string): Run | undefined => {
  const runs = getMockRuns();
  return runs.find((run) => run.id === runId);
};
