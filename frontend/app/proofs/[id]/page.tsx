"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { api, ApiError, ProofDetail, VerifyResult, getSession } from "@/lib/api";
import { TopNav } from "@/components/top-nav";

function CheckRow({ label, ok }: { label: string; ok: boolean | undefined }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-2 text-sm"
    >
      <span className={ok ? "text-risk-low" : "text-gray-600"}>{ok ? "✓" : "…"}</span>
      <span className={ok ? "text-gray-200" : "text-gray-500"}>{label}</span>
    </motion.div>
  );
}

export default function ProofDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [proof, setProof] = useState<ProofDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!getSession()) {
      router.replace("/login");
      return;
    }
    api
      .getProof(params.id)
      .then(setProof)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load proof"));
  }, [params.id, router]);

  async function verify() {
    setVerifying(true);
    setResult(null);
    setStep(0);
    try {
      const r = await api.verifyProof(params.id);
      const steps = [1, 2, 3];
      for (const s of steps) {
        await new Promise((res) => setTimeout(res, 350));
        setStep(s);
      }
      setResult(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verification failed");
    } finally {
      setVerifying(false);
    }
  }

  if (!proof) {
    return (
      <div>
        <TopNav />
        <div className="max-w-4xl mx-auto px-6 py-8 text-sm text-gray-500">{error ?? "Loading…"}</div>
      </div>
    );
  }

  const payload = proof.canonical_json;

  return (
    <div>
      <TopNav />
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Proof {proof.id}</div>
          <h1 className="text-xl font-semibold mt-1">{payload.decision_type} — {payload.case_id}</h1>
        </div>

        {error && <div className="panel p-3 text-sm text-risk-critical">{error}</div>}

        <div className="panel p-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-xs text-gray-500 uppercase">Confidence</div>
            <div className="tabular text-lg">{payload.confidence}%</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Risk Level</div>
            <div>{payload.risk_level}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Policy Version</div>
            <div>{payload.policy_version}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Model</div>
            <div>{payload.model} ({payload.model_version})</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Action</div>
            <div>{payload.action ?? "none"}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Human Approval</div>
            <div>{payload.human_approval ?? "not required"}</div>
          </div>
        </div>

        <div className="panel p-4">
          <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Evidence</div>
          <div className="space-y-1 text-sm">
            {payload.evidence?.map((e: any, i: number) => (
              <div key={i} className="flex justify-between border-b border-line/60 py-1 last:border-0">
                <span className="text-gray-500">{e.type}</span>
                <span className="tabular">{e.reference ?? e.id}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="panel p-4">
          <div className="text-xs uppercase tracking-wide text-gray-500 mb-2">Stored SHA-256</div>
          <div className="tabular text-xs break-all text-gray-400">{proof.sha256_hash}</div>
        </div>

        <div className="panel p-4 space-y-3">
          <button
            onClick={verify}
            disabled={verifying}
            className="rounded-md bg-accent text-ink-950 font-semibold px-4 py-2 text-sm disabled:opacity-50"
          >
            {verifying ? "Verifying…" : "VERIFY INTEGRITY"}
          </button>

          <AnimatePresence>
            {(verifying || result) && (
              <div className="space-y-1.5 pt-2">
                <CheckRow label="Canonical record reconstructed" ok={step >= 1 || !!result} />
                <CheckRow label="SHA-256 recomputed" ok={step >= 2 || !!result} />
                <CheckRow label="Hash matches stored proof" ok={step >= 3 && result?.hash_matches} />
                {result && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className={`mt-3 font-semibold ${result.verified ? "text-risk-low" : "text-risk-critical"}`}
                  >
                    {result.verified ? "PROOF VERIFIED" : "VERIFICATION FAILED"}
                  </motion.div>
                )}
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
