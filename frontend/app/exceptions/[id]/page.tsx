"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  api,
  ApiError,
  ExceptionSummary,
  InvestigationView,
  getSession,
} from "@/lib/api";
import { TopNav } from "@/components/top-nav";
import { DecisionBadge, ModeTag, RiskBadge, StatusBadge } from "@/components/badges";
import { ConfidenceMeter } from "@/components/confidence-meter";

const WORKER_LABELS: Record<string, string> = {
  EVIDENCE: "Evidence Worker",
  PAYMENT: "Payment Worker",
  POLICY: "Policy Worker",
  DECISION: "Decision Worker",
  AUDIT: "Audit Worker",
};

function GraphNode({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="panel px-4 py-3">
      <div className="text-sm font-medium">{title}</div>
      {subtitle && <div className="text-xs text-gray-500 mt-0.5">{subtitle}</div>}
    </div>
  );
}

export default function ExceptionDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [exc, setExc] = useState<ExceptionSummary | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [role, setRole] = useState<string>("");

  async function load() {
    const e = await api.getException(params.id);
    setExc(e);
    if (e.case_id) {
      const inv = await api.getInvestigation(e.case_id);
      setInvestigation(inv);
    }
  }

  useEffect(() => {
    const session = getSession();
    if (!session) {
      router.replace("/login");
      return;
    }
    setRole(session.role);
    load().catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load exception"));
  }, [params.id, router]);

  async function investigate() {
    setBusy(true);
    setError(null);
    try {
      await api.investigateException(params.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Investigation failed");
    } finally {
      setBusy(false);
    }
  }

  async function review(action: "approve" | "reject") {
    const decisionId = investigation?.case_state?.decision?.decision_id;
    if (!decisionId) return;
    setBusy(true);
    setError(null);
    try {
      if (action === "approve") await api.approveDecision(decisionId);
      else await api.rejectDecision(decisionId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Review action failed");
    } finally {
      setBusy(false);
    }
  }

  if (!exc) {
    return (
      <div>
        <TopNav />
        <div className="max-w-5xl mx-auto px-6 py-8 text-sm text-gray-500">{error ?? "Loading…"}</div>
      </div>
    );
  }

  const evidence = investigation?.case_state?.evidence;
  const payment = investigation?.case_state?.payment;
  const decision = investigation?.case_state?.decision;
  const policy = investigation?.case_state?.policy;
  const proofId = investigation?.case_state?.audit?.proof_id;
  const canReview = (role === "CFO" || role === "ADMIN") && investigation?.status === "AWAITING_APPROVAL";

  return (
    <div>
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Exception {exc.id}</div>
          <h1 className="text-2xl font-semibold mt-1 tabular">
            {exc.discrepancy_amount != null ? `$${Math.abs(exc.discrepancy_amount).toLocaleString()} discrepancy` : exc.exception_type}
          </h1>
          <div className="flex items-center gap-2 mt-2">
            <RiskBadge level={exc.risk_level} />
            <StatusBadge status={exc.status} />
            {payment?.source_mode && <ModeTag mode={payment.source_mode} />}
          </div>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        {!exc.case_id && (
          <button
            onClick={investigate}
            disabled={busy}
            className="rounded-md bg-accent text-ink-950 font-semibold px-4 py-2 text-sm disabled:opacity-50"
          >
            {busy ? "Investigating…" : "Investigate"}
          </button>
        )}

        {investigation && (
          <div className="grid md:grid-cols-2 gap-6">
            <div className="panel p-4">
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-3">Financial Graph</div>
              <div className="space-y-2">
                <GraphNode title={`Payment ${payment?.payment_id ?? "—"}`} subtitle={payment ? `$${payment.amount?.toLocaleString()} · ${payment.status}` : undefined} />
                <div className="pl-4 text-gray-600 text-xs">↓</div>
                <GraphNode
                  title={`Invoice ${evidence?.invoice_number ?? "not found"}`}
                  subtitle={evidence?.invoice_amount ? `$${evidence.invoice_amount.toLocaleString()} total` : undefined}
                />
                <div className="pl-4 text-gray-600 text-xs">↓</div>
                <GraphNode title={`Customer ${evidence?.customer_name ?? "—"}`} />
                <div className="pl-4 text-gray-600 text-xs">↓</div>
                <GraphNode title={`Contract ${evidence?.contract_name ?? "—"}`} />
                {evidence?.credit_memo_number && (
                  <>
                    <div className="pl-4 text-gray-600 text-xs">↓</div>
                    <GraphNode
                      title={`Credit Memo ${evidence.credit_memo_number}`}
                      subtitle={`$${Math.abs(evidence.credit_memo_amount ?? 0).toLocaleString()}`}
                    />
                  </>
                )}
                {evidence?.policy_version && (
                  <>
                    <div className="pl-4 text-gray-600 text-xs">↓</div>
                    <GraphNode title={`Policy ${evidence.policy_version}`} subtitle={policy?.matched_rule} />
                  </>
                )}
              </div>
            </div>

            <div className="panel p-4">
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-3">Live Investigation</div>
              <div className="space-y-2">
                {investigation.tasks.map((t) => (
                  <div key={t.id} className="flex items-center justify-between text-sm border-b border-line/60 pb-2 last:border-0">
                    <span>{WORKER_LABELS[t.worker_name] ?? t.worker_name}</span>
                    <div className="flex items-center gap-2">
                      {t.duration_ms != null && <span className="tabular text-xs text-gray-500">{t.duration_ms}ms</span>}
                      <StatusBadge status={t.status} />
                    </div>
                  </div>
                ))}
              </div>

              {decision && (
                <div className="mt-4 pt-4 border-t border-line space-y-3">
                  <div className="text-xs uppercase tracking-wide text-gray-500">AI Explanation</div>
                  <p className="text-sm text-gray-300">{decision.explanation}</p>
                  <div className="flex items-center justify-between">
                    <ConfidenceMeter value={decision.confidence} />
                    <DecisionBadge decision={decision.decision_type} />
                  </div>
                  <div className="text-xs text-gray-500">
                    Model: {decision.model} ({decision.inference_mode}) · Evidence: {evidence ? Object.values(evidence).filter(Boolean).length : 0} items
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {canReview && (
          <div className="panel p-4 flex items-center justify-between">
            <div className="text-sm text-gray-300">This decision requires human review before any action is taken.</div>
            <div className="flex gap-2">
              <button onClick={() => review("reject")} disabled={busy} className="rounded-md border border-line px-4 py-2 text-sm hover:border-risk-critical">
                Reject
              </button>
              <button onClick={() => review("approve")} disabled={busy} className="rounded-md bg-accent text-ink-950 font-semibold px-4 py-2 text-sm">
                Approve
              </button>
            </div>
          </div>
        )}

        {investigation?.trace_id && (
          <div className="flex gap-3">
            <Link href={`/traces/${investigation.trace_id}`} className="rounded-md border border-line px-4 py-2 text-sm hover:border-accent">
              VIEW TRACE
            </Link>
            {proofId && (
              <Link href={`/proofs/${proofId}`} className="rounded-md border border-line px-4 py-2 text-sm hover:border-accent">
                VIEW PROOF
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
