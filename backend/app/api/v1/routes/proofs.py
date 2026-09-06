import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.models.decisions import Decision
from app.models.observability import Span
from app.models.proofs import ProofCapsule

router = APIRouter(prefix="/proofs", tags=["proofs"])


def _serialize(proof: ProofCapsule) -> dict:
    return {
        "id": proof.id,
        "decision_id": proof.decision_id,
        "case_id": proof.case_id,
        "trace_id": proof.trace_id,
        "sha256_hash": proof.sha256_hash,
        "canonical_json": json.loads(proof.canonical_json),
        "created_at": proof.created_at.isoformat(),
    }


@router.get("")
def list_proofs(db: Session = Depends(get_db), limit: int = 25, offset: int = 0) -> dict:
    query = db.query(ProofCapsule).join(Decision, ProofCapsule.decision_id == Decision.id)
    total = query.count()
    items = query.order_by(ProofCapsule.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                **_serialize(p),
                "decision_type": db.get(Decision, p.decision_id).decision_type,
                "risk_level": db.get(Decision, p.decision_id).risk_level,
                "confidence": float(db.get(Decision, p.decision_id).confidence),
            }
            for p in items
        ],
        "total": total,
    }


@router.get("/{proof_id}")
def get_proof(proof_id: str, db: Session = Depends(get_db)) -> dict:
    proof = db.get(ProofCapsule, proof_id)
    if proof is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proof not found")
    return _serialize(proof)


@router.post("/{proof_id}/verify")
def verify_proof(proof_id: str, db: Session = Depends(get_db)) -> dict:
    proof = db.get(ProofCapsule, proof_id)
    if proof is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proof not found")

    recomputed_hash = hashlib.sha256(proof.canonical_json.encode()).hexdigest()
    hash_matches = recomputed_hash == proof.sha256_hash

    decision = db.get(Decision, proof.decision_id)
    payload = json.loads(proof.canonical_json)

    decision_record_intact = (
        decision is not None
        and decision.decision_type == payload.get("decision_type")
        and float(decision.confidence) == payload.get("confidence")
        and decision.action_taken == payload.get("action")
    )

    trace_spans_count = db.query(Span).filter(Span.trace_id == proof.trace_id).count() if proof.trace_id else 0
    trace_reference_intact = trace_spans_count == len(payload.get("tool_calls", []))

    return {
        "proof_id": proof_id,
        "canonical_record_reconstructed": True,
        "recomputed_sha256": recomputed_hash,
        "stored_sha256": proof.sha256_hash,
        "hash_matches": hash_matches,
        "decision_record_intact": decision_record_intact,
        "trace_reference_intact": trace_reference_intact,
        "verified": hash_matches and decision_record_intact and trace_reference_intact,
    }
