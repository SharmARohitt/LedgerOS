"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, setSession } from "@/lib/api";

const QUICK_LOGINS = [
  { email: "cfo@ledgeros.dev", role: "CFO" },
  { email: "analyst@ledgeros.dev", role: "Finance Analyst" },
  { email: "auditor@ledgeros.dev", role: "Auditor" },
  { email: "admin@ledgeros.dev", role: "Admin" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("cfo@ledgeros.dev");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      setSession(res.access_token, res.role, res.name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to reach LedgerOS API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="text-2xl font-semibold tracking-wide">
            LEDGER<span className="text-accent">OS</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">The Autonomous Financial Control Plane</p>
        </div>

        <form onSubmit={submit} className="panel p-6 space-y-4">
          <div>
            <label className="text-xs text-gray-400">Email</label>
            <input
              className="mt-1 w-full rounded-md bg-ink-800 border border-line px-3 py-2 text-sm outline-none focus:border-accent"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Password</label>
            <input
              type="password"
              className="mt-1 w-full rounded-md bg-ink-800 border border-line px-3 py-2 text-sm outline-none focus:border-accent"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <p className="text-xs text-risk-critical">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-accent text-ink-950 font-semibold py-2 text-sm disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Enter Control Center"}
          </button>
        </form>

        <div className="mt-4 panel p-4">
          <p className="text-xs text-gray-500 mb-2">Seeded demo accounts — enter your SEED_PASSWORD</p>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_LOGINS.map((u) => (
              <button
                key={u.email}
                onClick={() => setEmail(u.email)}
                className="text-xs text-left rounded border border-line px-2 py-1.5 hover:border-accent"
              >
                {u.role}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
