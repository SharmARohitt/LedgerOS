from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.domain.events.ingestion import ingest_dodo_payload
from app.integrations.dodo.mock import MockDodoProvider
from app.models.finance import Invoice

router = APIRouter(prefix="/demo", tags=["demo"])

# CASE 01 (spec section 34): $48,750 Dodo payment against a $50,000 invoice,
# fully explained by a $1,250 SLA credit memo -> AUTO_RESOLVE.
CASE_01_INVOICE_NUMBER = "INV-4821"
CASE_01_PAYMENT_AMOUNT = 48750.00


@router.post("/run-case-01")
def run_case_01(db: Session = Depends(get_db)) -> dict:
    invoice = db.query(Invoice).filter(Invoice.invoice_number == CASE_01_INVOICE_NUMBER).one_or_none()
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=f"Seed data missing: invoice {CASE_01_INVOICE_NUMBER} not found. Run the seed script first.",
        )

    provider = MockDodoProvider()
    payload = provider.simulate_payment(
        amount=CASE_01_PAYMENT_AMOUNT,
        currency="USD",
        invoice_reference=CASE_01_INVOICE_NUMBER,
        customer_reference=invoice.customer_id,
    )
    result = ingest_dodo_payload(db, payload, source_mode="SIMULATED")
    return {**result, "demo_case": "CASE_01"}
