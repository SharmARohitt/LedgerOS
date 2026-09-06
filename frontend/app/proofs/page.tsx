"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, ProofSummary, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";
import { DecisionBadge, RiskBadge } from "@/components/badges";

export default function ProofCenterPage() {
  const router = useRouter();
  const [proofs, setProofs] = useState<ProofSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    api
      .listProofs()
      .then((r) => setProofs(r.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load proofs"));
  }, [router]);

  return (
    <div>
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">FINANCIAL PROOF CENTER</h1>
          <p className="text-sm text-gray-500">Tamper-evident decision certificates — every automated action, proven.</p>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        <div className="panel overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-gray-500 border-b border-line">
                <th className="text-left px-4 py-3">Case</th>
                <th className="text-left px-4 py-3">Decision</th>
                <th className="text-left px-4 py-3">Risk</th>
                <th className="text-left px-4 py-3">Confidence</th>
                <th className="text-left px-4 py-3">Hash</th>
                <th className="text-left px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {proofs.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => router.push(`/proofs/${p.id}`)}
                  className="border-b border-line/60 last:border-0 cursor-pointer hover:bg-ink-800/60"
                >
                  <td className="px-4 py-3 tabular">{p.case_id}</td>
                  <td className="px-4 py-3">
                    <DecisionBadge decision={p.decision_type} />
                  </td>
                  <td className="px-4 py-3">
                    <RiskBadge level={p.risk_level} />
                  </td>
                  <td className="px-4 py-3 tabular">{p.confidence.toFixed(1)}%</td>
                  <td className="px-4 py-3 tabular text-gray-500">{p.sha256_hash.slice(0, 16)}…</td>
                  <td className="px-4 py-3 text-gray-500">{new Date(p.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {proofs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                    No proofs yet — resolve an exception to generate one.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
