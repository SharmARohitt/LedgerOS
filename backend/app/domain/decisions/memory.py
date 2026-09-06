"""Organizational decision memory: retrieve similar historical cases by
pattern (policy_key + amount band). Purely advisory — it informs confidence,
it never silently changes a policy. Promotion to policy is a separate,
human-gated action (out of scope for the vertical slice)."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.decisions import Decision, DecisionMemoryEntry


@dataclass
class SimilarCaseStats:
    pattern_key: str
    total_cases: int
    approved: int
    rejected: int

    @property
    def approval_rate(self) -> float | None:
        decided = self.approved + self.rejected
        return round(self.approved / decided, 4) if decided else None


def amount_band(amount: float) -> str:
    if amount < 1000:
        return "lt_1k"
    if amount < 2500:
        return "1k_2.5k"
    if amount < 5000:
        return "2.5k_5k"
    if amount < 25000:
        return "5k_25k"
    return "gte_25k"


def make_pattern_key(policy_key: str | None, amount: float) -> str:
    return f"{policy_key or 'no_policy'}:{amount_band(amount)}"


def find_similar_cases(db: Session, pattern_key: str) -> SimilarCaseStats:
    entries = (
        db.query(DecisionMemoryEntry, Decision)
        .join(Decision, DecisionMemoryEntry.decision_id == Decision.id)
        .filter(DecisionMemoryEntry.pattern_key == pattern_key)
        .all()
    )
    approved = sum(1 for e, _ in entries if e.human_outcome == "APPROVED")
    rejected = sum(1 for e, _ in entries if e.human_outcome == "REJECTED")
    return SimilarCaseStats(pattern_key=pattern_key, total_cases=len(entries), approved=approved, rejected=rejected)


def record_decision_memory(db: Session, decision: Decision, pattern_key: str) -> DecisionMemoryEntry:
    entry = DecisionMemoryEntry(pattern_key=pattern_key, decision_id=decision.id, learning_stage="ADVISORY")
    db.add(entry)
    db.flush()
    return entry
