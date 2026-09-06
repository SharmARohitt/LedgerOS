const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("ledgeros_token");
}

export function setSession(token: string, role: string, name: string) {
  window.localStorage.setItem("ledgeros_token", token);
  window.localStorage.setItem("ledgeros_role", role);
  window.localStorage.setItem("ledgeros_name", name);
}

export function clearSession() {
  window.localStorage.removeItem("ledgeros_token");
  window.localStorage.removeItem("ledgeros_role");
  window.localStorage.removeItem("ledgeros_name");
}

export function getSession(): { token: string; role: string; name: string } | null {
  const token = getToken();
  if (!token) return null;
  return {
    token,
    role: window.localStorage.getItem("ledgeros_role") || "",
    name: window.localStorage.getItem("ledgeros_name") || "",
  };
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---- Types ----

export interface LoginResponse {
  access_token: string;
  role: string;
  name: string;
}

export interface DashboardOverview {
  transactions_processed: number;
  total_volume: number;
  exceptions_detected: number;
  exceptions_open: number;
  at_risk_capital: number;
  exceptions_auto_resolved: number;
  human_escalations: number;
  blocked_actions: number;
  average_investigation_time_ms: number | null;
  estimated_inference_cost: number;
  evidence_count: number;
  proofs_generated: number;
}

export interface ExceptionSummary {
  id: string;
  event_id: string;
  exception_type: string;
  status: string;
  discrepancy_amount: number | null;
  risk_score: number;
  risk_level: string;
  summary: string;
  invoice_number: string | null;
  customer_name: string | null;
  created_at: string;
  case_id?: string;
  case_status?: string;
}

export interface CaseTaskView {
  id: string;
  worker_name: string;
  status: string;
  duration_ms: number | null;
  error: string | null;
  output: Record<string, unknown>;
  created_at: string;
}

export interface InvestigationView {
  id: string;
  exception_id: string;
  trace_id: string | null;
  status: string;
  case_state: Record<string, any>;
  tasks: CaseTaskView[];
}

export interface SpanView {
  id: string;
  parent_span_id: string | null;
  agent_id: string;
  tool_name: string;
  tool_arguments_hash: string;
  model: string | null;
  model_version: string | null;
  prompt_version: string | null;
  inference_mode: string | null;
  policy_version: string | null;
  risk_level: string | null;
  decision: string | null;
  confidence: number | null;
  human_approval: string | null;
  status: string;
  error: string | null;
  retry_count: number;
  duration_ms: number | null;
  cost_estimate: number;
  created_at: string;
}

export interface TraceView {
  id: string;
  case_id: string | null;
  workflow_id: string;
  status: string;
  duration_ms: number | null;
  total_cost_estimate: number;
  spans: SpanView[];
}

export interface ProofSummary {
  id: string;
  decision_id: string;
  case_id: string;
  trace_id: string | null;
  sha256_hash: string;
  canonical_json: Record<string, any>;
  created_at: string;
  decision_type: string;
  risk_level: string;
  confidence: number;
}

export interface ProofDetail {
  id: string;
  decision_id: string;
  case_id: string;
  trace_id: string | null;
  sha256_hash: string;
  canonical_json: Record<string, any>;
  created_at: string;
}

export interface VerifyResult {
  proof_id: string;
  canonical_record_reconstructed: boolean;
  recomputed_sha256: string;
  stored_sha256: string;
  hash_matches: boolean;
  decision_record_intact: boolean;
  trace_reference_intact: boolean;
  verified: boolean;
}

// ---- Calls ----

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  dashboardOverview: () => request<DashboardOverview>("/dashboard/overview"),

  listExceptions: (status?: string) =>
    request<{ items: ExceptionSummary[]; total: number }>(`/exceptions${status ? `?status=${status}` : ""}`),

  getException: (id: string) => request<ExceptionSummary>(`/exceptions/${id}`),

  investigateException: (id: string) => request<any>(`/exceptions/${id}/investigate`, { method: "POST" }),

  getInvestigation: (caseId: string) => request<InvestigationView>(`/investigations/${caseId}`),

  getTrace: (traceId: string) => request<TraceView>(`/traces/${traceId}`),

  listProofs: () => request<{ items: ProofSummary[]; total: number }>("/proofs"),

  getProof: (id: string) => request<ProofDetail>(`/proofs/${id}`),

  verifyProof: (id: string) => request<VerifyResult>(`/proofs/${id}/verify`, { method: "POST" }),

  runCase01: () => request<any>("/demo/run-case-01", { method: "POST" }),

  approveDecision: (decisionId: string, note?: string) =>
    request<any>(`/decisions/${decisionId}/approve`, { method: "POST", body: JSON.stringify({ note }) }),

  rejectDecision: (decisionId: string, note?: string) =>
    request<any>(`/decisions/${decisionId}/reject`, { method: "POST", body: JSON.stringify({ note }) }),
};
