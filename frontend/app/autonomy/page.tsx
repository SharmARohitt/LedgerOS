"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, AutonomyCapability, PolicyView, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";

export default function AutonomyControlPage() {
  const router = useRouter();
  const [capabilities, setCapabilities] = useState<AutonomyCapability[]>([]);
  const [principle, setPrinciple] = useState("");
  const [policies, setPolicies] = useState<PolicyView[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    Promise.all([api.autonomyMatrix(), api.listPolicies()])
      .then(([matrix, pol]) => {
        setCapabilities(matrix.capabilities);
        setPrinciple(matrix.principle);
        setPolicies(pol.items);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load autonomy governance"));
  }, [router]);

  return (
    <div>
      <TopNav />
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-lg font-semibold tracking-wide">AUTONOMY GOVERNANCE</h1>
          <p className="text-sm text-gray-500">{principle}</p>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        <div className="panel divide-y divide-line">
          {capabilities.map((c) => (
            <div key={c.capability} className="flex items-center justify-between px-4 py-2.5 text-sm">
              <span className="text-gray-300">{c.capability.replace(/_/g, " ")}</span>
              <span className={c.allowed ? "text-risk-low font-semibold" : "text-risk-critical font-semibold"}>
                {c.allowed ? "✓ ALLOWED" : "✕ BLOCKED"}
              </span>
            </div>
          ))}
        </div>

        <div>
          <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Active Policies</div>
          <div className="panel divide-y divide-line">
            {policies.map((p) => (
              <div key={p.id} className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium">{p.policy_key}</div>
                  <span className="badge text-accent">{p.version}</span>
                </div>
                <div className="text-xs text-gray-500 mt-1">{p.description}</div>
                <div className="text-xs text-gray-600 mt-1 font-mono">{JSON.stringify(p.rules)}</div>
              </div>
            ))}
            {policies.length === 0 && <div className="px-4 py-3 text-sm text-gray-500">No policies configured.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
