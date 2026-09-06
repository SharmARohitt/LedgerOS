"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, ApiError, FinancialTwinSnapshot, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";

const money = (n: number) => `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

const RISK_TEXT: Record<string, string> = { LOW: "text-risk-low", MEDIUM: "text-risk-medium", HIGH: "text-risk-critical" };
const SEVERITY_TEXT: Record<string, string> = { LOW: "text-gray-400", MEDIUM: "text-risk-medium", HIGH: "text-risk-critical" };

function Section({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs uppercase tracking-wide text-gray-500">{title}</div>
        {action}
      </div>
      {children}
    </div>
  );
}

function CapitalNode({ label, value, indent = 0 }: { label: string; value: number; indent?: number }) {
  return (
    <div className="flex items-center justify-between py-1.5 text-sm" style={{ paddingLeft: indent * 16 }}>
      <span className="text-gray-400">{label}</span>
      <span className="tabular font-medium">{money(value)}</span>
    </div>
  );
}

export default function FinancialTwinPage() {
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<FinancialTwinSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    api
      .financialTwinOverview()
      .then(setSnapshot)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load Financial Twin"));
  }, [router]);

  return (
    <div>
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">FINANCIAL TWIN</h1>
          <p className="text-sm text-gray-500">
            A continuously recalculated model of the company&apos;s capital position — not a static report.
            {snapshot && <span className="text-gray-600"> As of {snapshot.as_of}.</span>}
          </p>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        {snapshot && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Section title="Capital Map">
                <CapitalNode label="Total Capital" value={snapshot.capital_map.total_capital} />
                <CapitalNode label="Operating Cash" value={snapshot.capital_map.operating_cash} indent={1} />
                <CapitalNode label="Reserve" value={snapshot.capital_map.reserve} indent={1} />
                <CapitalNode label="Expected Inflows (30d)" value={snapshot.capital_map.expected_inflows} indent={1} />
                <CapitalNode label="Committed Outflows (30d)" value={-snapshot.capital_map.committed_outflows} indent={1} />
                <div className="border-t border-line mt-2 pt-2">
                  <CapitalNode label="Potentially Deployable" value={snapshot.capital_map.deployable_capital} />
                </div>
                {snapshot.policy_version && (
                  <div className="text-xs text-gray-600 mt-2">
                    Reserve requirement per capital policy {snapshot.policy_version}
                  </div>
                )}
              </Section>

              <Section title="Liquidity & Forecast">
                <CapitalNode label="Available Cash" value={snapshot.liquidity.available_cash} />
                <CapitalNode label="Expected Inflows (30d)" value={snapshot.liquidity.expected_inflows_30d} />
                <CapitalNode label="Expected Outflows (30d)" value={-snapshot.liquidity.expected_outflows_30d} />
                <CapitalNode label="Net 30-Day Position" value={snapshot.liquidity.net_30d_position} />
                <div className="flex items-center justify-between py-1.5 text-sm">
                  <span className="text-gray-400">Runway</span>
                  <span className="tabular font-medium">
                    {snapshot.liquidity.runway_months != null ? `${snapshot.liquidity.runway_months} months` : "—"}
                  </span>
                </div>
              </Section>
            </div>

            <Section title="Obligations">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Object.entries(snapshot.obligations.by_type).map(([type, amount]) => (
                  <div key={type}>
                    <div className="text-xs text-gray-500">{type}</div>
                    <div className="tabular text-sm font-medium">{money(amount)}</div>
                  </div>
                ))}
                {Object.entries(snapshot.obligations.by_type).length === 0 && (
                  <div className="text-sm text-gray-500 col-span-full">No scheduled obligations.</div>
                )}
              </div>
            </Section>

            <Section
              title="Deployment Opportunities"
              action={
                <Link href="/scenarios" className="text-xs text-accent hover:underline">
                  RUN SCENARIO →
                </Link>
              }
            >
              {snapshot.deployment_opportunities.length === 0 && (
                <div className="text-sm text-gray-500">No deployable capital available right now — cash is within reserve targets.</div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {snapshot.deployment_opportunities.map((opp) => (
                  <div key={opp.category} className="rounded-md border border-line p-3">
                    <div className="text-xs text-gray-500">OPTION {opp.rank}</div>
                    <div className="text-sm font-semibold mt-0.5">{opp.label}</div>
                    <div className="tabular text-xl font-semibold mt-1">{money(opp.amount)}</div>
                    <div className="text-xs text-gray-500 mt-2 space-y-0.5">
                      <div>
                        Liquidity Impact: <span className="text-gray-300">{opp.liquidity_impact}</span>
                      </div>
                      <div>
                        Risk: <span className={RISK_TEXT[opp.risk] ?? "text-gray-300"}>{opp.risk}</span>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 mt-2">{opp.reason}</div>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="badge text-accent">{opp.status.replace("_", " ")}</span>
                      <span className="text-[10px] text-gray-600">{opp.projection_label}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Section>

            <Section title="Early Warning">
              {snapshot.early_warnings.length === 0 && (
                <div className="text-sm text-gray-500">No active warnings — all signals within policy thresholds.</div>
              )}
              <div className="space-y-3">
                {snapshot.early_warnings.map((w) => (
                  <div key={w.signal} className="rounded-md border border-line p-3">
                    <div className={`text-sm font-semibold ${SEVERITY_TEXT[w.severity] ?? "text-gray-300"}`}>
                      ⚠ {w.signal.replace(/_/g, " ")}
                    </div>
                    <div className="text-sm text-gray-400 mt-1">{w.evidence}</div>
                    <div className="text-xs text-gray-500 mt-2">Recommended: {w.recommended_action}</div>
                  </div>
                ))}
              </div>
            </Section>
          </>
        )}
      </div>
    </div>
  );
}
