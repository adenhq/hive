import { RunTable } from "@/components/run-table";
import { getMockRuns } from "@/lib/data-adapter";

const RunsPage = () => {
  const runs = getMockRuns();

  if (runs.length === 0) {
    return (
      <main className="flex flex-col gap-6">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
            Agent Runs
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-300">
            No runs have been recorded yet.
          </p>
        </header>
      </main>
    );
  }

  return (
    <main className="flex flex-col gap-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Agent Runs
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Inspect recent runs and drill into execution steps.
        </p>
      </header>
      <RunTable runs={runs} />
    </main>
  );
};

export default RunsPage;
