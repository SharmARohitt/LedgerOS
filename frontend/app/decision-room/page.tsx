"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, DecisionRoomItem, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";
import { RiskBadge, DecisionBadge } from "@/components/badges";

const money = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

export default function DecisionRoomPage() {
  const router = useRouter();
  const [pendingCount, setPendingCount] = useState(0);
  const [totalExposure, setTotalExposure] = useState(0);
  const [items, setItems] = useState<DecisionRoomItem[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const res = await api.decisionRoom();
    setPendingCount(res.pending_count);
    setTotalExposure(res.total_exposure);
    setItems(res.items);
  }

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    load().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load Decision Room"));
  }, [router]);

  async function act(decisionId: string, action: "approve" | "reject") {
    setBusyId(decisionId);
    setError(null);
    try {
      if (action === "approve") await api.approveDecision(decisionId);
      else await api.rejectDecision(decisionId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Failed to ${action}`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">DECISION ROOM</h1>
          <p className="text-sm text-gray-500">
            {pendingCount} decision{pendingCount === 1 ? "" : "s"} require review · Total exposure {money(totalExposure)}
          </p>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        <div className="panel divide-y divide-line">
          {items.length === 0 && <div className="p-4 text-sm text-gray-500">No decisions currently awaiting review.</div>}
          {items.map((item) => (
            <div key={item.decision_id} className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="tabular text-lg font-semibold">{money(item.amount)}</span>
                    <DecisionBadge decision={item.recommendation} />
                    <RiskBadge level={item.risk_level} />
                  </div>
                  <div className="text-sm text-gray-400 mt-1">{item.reason}</div>
                  <div className="text-xs text-gray-600 mt-1">
                    Confidence {item.confidence.toFixed(1)}% · Policy {item.policy_version ?? "—"} · Evidence {item.evidence_count} items ·{" "}
                    <Link href={`/exceptions/${item.exception_id}`} className="text-accent hover:underline">
                      view investigation
                    </Link>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => act(item.decision_id, "approve")}
                    disabled={busyId === item.decision_id}
                    className="rounded-md bg-risk-low/20 text-risk-low border border-risk-low px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                  >
                    APPROVE
                  </button>
                  <button
                    onClick={() => act(item.decision_id, "reject")}
                    disabled={busyId === item.decision_id}
                    className="rounded-md bg-risk-critical/20 text-risk-critical border border-risk-critical px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                  >
                    REJECT
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
