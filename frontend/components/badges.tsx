const RISK_COLORS: Record<string, string> = {
  LOW: "text-risk-low",
  MEDIUM: "text-risk-medium",
  HIGH: "text-risk-high",
  CRITICAL: "text-risk-critical",
  UNKNOWN: "text-gray-500",
};

export function RiskBadge({ level }: { level: string }) {
  return <span className={`badge ${RISK_COLORS[level] ?? "text-gray-500"}`}>{level}</span>;
}

const DECISION_COLORS: Record<string, string> = {
  AUTO_RESOLVE: "text-risk-low",
  HUMAN_REVIEW: "text-risk-medium",
  BLOCK: "text-risk-critical",
};

export function DecisionBadge({ decision }: { decision: string }) {
  return <span className={`badge ${DECISION_COLORS[decision] ?? "text-gray-400"}`}>{decision.replace("_", " ")}</span>;
}

const STATUS_COLORS: Record<string, string> = {
  OPEN: "text-risk-medium",
  INVESTIGATING: "text-accent",
  RESOLVED: "text-risk-low",
  BLOCKED: "text-risk-critical",
  RUNNING: "text-accent",
  SUCCESS: "text-risk-low",
  FAILED: "text-risk-critical",
  COMPLETED: "text-risk-low",
  AWAITING_APPROVAL: "text-risk-medium",
  PENDING: "text-risk-medium",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${STATUS_COLORS[status] ?? "text-gray-400"}`}>{status.replace(/_/g, " ")}</span>;
}

const MODE_COLORS: Record<string, string> = {
  LIVE: "text-risk-low",
  SANDBOX: "text-accent",
  SIMULATED: "text-gray-500",
  FALLBACK: "text-gray-500",
};

export function ModeTag({ mode }: { mode: string }) {
  const normalized = mode in MODE_COLORS ? mode : "SIMULATED";
  return <span className={`badge ${MODE_COLORS[normalized]}`}>{normalized}</span>;
}
