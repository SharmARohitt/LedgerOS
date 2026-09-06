"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError, TraceView, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";
import { StatusBadge } from "@/components/badges";

export default function TraceExplorerPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [trace, setTrace] = useState<TraceView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    api
      .getTrace(params.id)
      .then(setTrace)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load trace"));
  }, [params.id, router]);

  if (!trace) {
    return (
      <div>
        <TopNav />
        <div className="max-w-5xl mx-auto px-6 py-8 text-sm text-gray-500">{error ?? "Loading…"}</div>
      </div>
    );
  }

  const maxDuration = Math.max(...trace.spans.map((s) => s.duration_ms ?? 0), 1);

  return (
    <div>
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Trace {trace.id}</div>
          <div className="flex items-center gap-3 mt-1">
            <h1 className="text-xl font-semibold">{trace.workflow_id}</h1>
            <StatusBadge status={trace.status} />
          </div>
          <div className="text-sm text-gray-500 mt-1 tabular">
            {trace.duration_ms}ms total · ${trace.total_cost_estimate.toFixed(4)} estimated inference cost
          </div>
        </div>

        <div className="panel p-4 space-y-3">
          {trace.spans.map((s) => (
            <div key={s.id} className="border-b border-line/60 pb-3 last:border-0">
              <div className="flex items-center justify-between text-sm">
                <div className="font-medium">{s.agent_id}</div>
                <StatusBadge status={s.status} />
              </div>
              <div className="text-xs text-gray-500">{s.tool_name}</div>
              <div className="mt-2 h-2 rounded bg-ink-700 overflow-hidden">
                <div
                  className="h-full bg-accent-dim"
                  style={{ width: `${((s.duration_ms ?? 0) / maxDuration) * 100}%` }}
                />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-500 tabular">
                <span>{s.duration_ms ?? 0}ms</span>
                {s.model && <span>model: {s.model}</span>}
                {s.inference_mode && <span>mode: {s.inference_mode}</span>}
                {s.decision && <span>decision: {s.decision}</span>}
                {s.confidence != null && <span>confidence: {s.confidence}%</span>}
                {s.risk_level && <span>risk: {s.risk_level}</span>}
                {s.policy_version && <span>policy: {s.policy_version}</span>}
                <span>cost: ${s.cost_estimate.toFixed(4)}</span>
                <span title={s.tool_arguments_hash}>args_hash: {s.tool_arguments_hash.slice(0, 12)}…</span>
              </div>
              {s.error && <div className="mt-1 text-xs text-risk-critical">{s.error}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
