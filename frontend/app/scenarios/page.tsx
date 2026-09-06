"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, ScenarioResult, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";

const money = (n: number | null) => (n == null ? "—" : `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`);
const signedMoney = (n: number | null) => (n == null ? "—" : `${n >= 0 ? "+" : ""}${money(n)}`);

const SCENARIOS: { type: string; label: string; question: string; paramKey: "pct" | "days"; defaultValue: number; unit: string }[] = [
  { type: "REVENUE_CHANGE", label: "Revenue Change", question: "What happens if revenue changes by", paramKey: "pct", defaultValue: -20, unit: "%" },
  { type: "COLLECTIONS_CHANGE", label: "Collections Change", question: "What happens if collections fall/rise by", paramKey: "pct", defaultValue: -20, unit: "%" },
  { type: "FUNDING_CHANGE", label: "Funding Change", question: "What happens if funding increases/decreases by", paramKey: "pct", defaultValue: 20, unit: "%" },
  { type: "EXPENSE_CHANGE", label: "Expense Change", question: "What happens if expenses change by", paramKey: "pct", defaultValue: 15, unit: "%" },
  { type: "DELAY_PAYMENT", label: "Delay Payment", question: "What happens if we delay obligations by", paramKey: "days", defaultValue: 15, unit: "days" },
];

function DeltaLine({ label, value, unit = "" }: { label: string; value: number | null; unit?: string }) {
  const positive = (value ?? 0) >= 0;
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-gray-400">{label}</span>
      <span className={`tabular font-medium ${positive ? "text-risk-low" : "text-risk-critical"}`}>
        {value == null ? "—" : `${value >= 0 ? "+" : ""}${value}${unit}`}
      </span>
    </div>
  );
}

export default function ScenarioLabPage() {
  const router = useRouter();
  const [scenarioType, setScenarioType] = useState(SCENARIOS[0].type);
  const [magnitude, setMagnitude] = useState(SCENARIOS[0].defaultValue);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getSession()) router.replace("/login");
  }, [router]);

  const active = SCENARIOS.find((s) => s.type === scenarioType)!;

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const params = { [active.paramKey]: magnitude };
      const res = await api.createScenario(scenarioType, params, `${active.label} (${magnitude}${active.unit})`);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to run scenario");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <TopNav />
      <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">FINANCIAL WHAT-IF ENGINE</h1>
          <p className="text-sm text-gray-500">Every result below is a simulated projection — not an actual financial forecast.</p>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        <div className="panel p-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            {SCENARIOS.map((s) => (
              <button
                key={s.type}
                onClick={() => {
                  setScenarioType(s.type);
                  setMagnitude(s.defaultValue);
                  setResult(null);
                }}
                className={`badge cursor-pointer ${scenarioType === s.type ? "text-accent" : "text-gray-500"}`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">{active.question}</span>
            <input
              type="number"
              value={magnitude}
              onChange={(e) => setMagnitude(Number(e.target.value))}
              className="tabular w-24 rounded-md bg-ink-800 border border-line px-2 py-1 text-sm"
            />
            <span className="text-sm text-gray-400">{active.unit}?</span>
            <button
              onClick={run}
              disabled={running}
              className="ml-auto rounded-md bg-accent text-ink-950 font-semibold px-4 py-2 text-sm disabled:opacity-50"
            >
              {running ? "Simulating…" : "SIMULATE"}
            </button>
          </div>
        </div>

        {result && (
          <>
            <div className="text-xs text-gray-600 uppercase tracking-wide">{result.label}</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="panel p-4">
                <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Baseline</div>
                <div className="tabular text-2xl font-semibold">{money(result.baseline.cash.total_cash)}</div>
                <div className="text-xs text-gray-500">Total Cash</div>
                <div className="mt-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Deployable Capital</span>
                    <span className="tabular">{money(result.baseline.capital_map.deployable_capital)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Runway</span>
                    <span className="tabular">{result.baseline.liquidity.runway_months ?? "—"} mo</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Liquidity Score</span>
                    <span className="tabular">{result.baseline.financial_health.liquidity_score}</span>
                  </div>
                </div>
              </div>
              <div className="panel p-4 border-accent/40">
                <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Scenario</div>
                <div className="tabular text-2xl font-semibold">{money(result.scenario.cash.total_cash)}</div>
                <div className="text-xs text-gray-500">Total Cash</div>
                <div className="mt-3 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Deployable Capital</span>
                    <span className="tabular">{money(result.scenario.capital_map.deployable_capital)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Runway</span>
                    <span className="tabular">{result.scenario.liquidity.runway_months ?? "—"} mo</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Liquidity Score</span>
                    <span className="tabular">{result.scenario.financial_health.liquidity_score}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="panel p-4">
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Impact</div>
              <DeltaLine label="Total Cash" value={result.deltas.total_cash} />
              <DeltaLine label="Deployable Capital" value={result.deltas.deployable_capital} />
              <DeltaLine label="Net 30-Day Position" value={result.deltas.net_30d_position} />
              <DeltaLine label="Runway" value={result.deltas.runway_months} unit=" mo" />
              <DeltaLine label="Liquidity Score" value={result.deltas.liquidity_score} unit=" pts" />
            </div>

            {result.scenario.early_warnings.length > 0 && (
              <div className="panel p-4">
                <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Warnings Under This Scenario</div>
                <div className="space-y-2">
                  {result.scenario.early_warnings.map((w) => (
                    <div key={w.signal} className="text-sm">
                      <span className="text-risk-critical font-medium">⚠ {w.signal.replace(/_/g, " ")}</span>
                      <span className="text-gray-400"> — {w.evidence}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
