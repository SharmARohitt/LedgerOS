"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, DashboardOverview, ExceptionSummary, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";
import { RiskBadge, StatusBadge } from "@/components/badges";
import Link from "next/link";

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="panel p-4">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="tabular text-2xl font-semibold mt-1">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

const money = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

export default function DashboardPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [exceptions, setExceptions] = useState<ExceptionSummary[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const [ov, exc] = await Promise.all([api.dashboardOverview(), api.listExceptions()]);
    setOverview(ov);
    setExceptions(exc.items);
  }

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    load().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load dashboard"));
  }, [router]);

  async function runLiveInvestigation() {
    setRunning(true);
    setError(null);
    try {
      const result = await api.runCase01();
      await load();
      if (result.exception_id) {
        router.push(`/exceptions/${result.exception_id}`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to run investigation");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-wide">LIVE FINANCIAL CONTROL</h1>
            <p className="text-sm text-gray-500">Every dollar. Every decision. Every action. Proven.</p>
          </div>
          <button
            onClick={runLiveInvestigation}
            disabled={running}
            className="rounded-md bg-accent text-ink-950 font-semibold px-4 py-2 text-sm disabled:opacity-50"
          >
            {running ? "Running investigation…" : "RUN LIVE INVESTIGATION"}
          </button>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Total Volume" value={money(overview.total_volume)} />
            <Metric label="Exceptions Detected" value={String(overview.exceptions_detected)} sub={`${overview.exceptions_open} open`} />
            <Metric label="At-Risk Capital" value={money(overview.at_risk_capital)} />
            <Metric label="Auto-Resolved" value={String(overview.exceptions_auto_resolved)} />
            <Metric label="Human Reviews" value={String(overview.human_escalations)} />
            <Metric label="Blocked" value={String(overview.blocked_actions)} />
            <Metric
              label="Avg. Investigation Time"
              value={overview.average_investigation_time_ms != null ? `${Math.round(overview.average_investigation_time_ms)}ms` : "—"}
            />
            <Metric label="Inference Cost" value={`$${overview.estimated_inference_cost.toFixed(4)}`} sub="illustrative" />
          </div>
        )}

        <div className="panel">
          <div className="px-4 py-3 border-b border-line text-xs uppercase tracking-wide text-gray-500">
            Exception Queue
          </div>
          <div className="divide-y divide-line">
            {exceptions.length === 0 && <div className="p-4 text-sm text-gray-500">No exceptions yet — run a live investigation to populate the queue.</div>}
            {exceptions.map((e) => (
              <Link
                key={e.id}
                href={`/exceptions/${e.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-ink-800/60 transition-colors"
              >
                <div>
                  <div className="text-sm font-medium">
                    {e.discrepancy_amount != null ? `$${Math.abs(e.discrepancy_amount).toLocaleString()} discrepancy` : e.exception_type}
                    {e.customer_name && <span className="text-gray-500"> · {e.customer_name}</span>}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {e.invoice_number ? `Invoice ${e.invoice_number}` : "No matching invoice"} · {new Date(e.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <RiskBadge level={e.risk_level} />
                  <StatusBadge status={e.status} />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
