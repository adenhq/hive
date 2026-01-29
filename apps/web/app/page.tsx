import Link from "next/link";

const HomePage = () => {
  return (
    <main className="flex flex-col gap-6">
      <header className="space-y-2">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Hive Observability
        </p>
        <h1 className="text-3xl font-semibold text-slate-900 dark:text-slate-100">
          Agent Runs
        </h1>
        <p className="max-w-2xl text-base text-slate-600 dark:text-slate-300">
          Review recent Hive runs and inspect execution steps for failures,
          retries, and outputs.
        </p>
      </header>
      <div>
        <Link
          href="/runs"
          aria-label="View all agent runs"
          className="inline-flex items-center rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-900 shadow-sm transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
        >
          View runs
        </Link>
      </div>
    </main>
  );
};

export default HomePage;
