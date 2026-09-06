from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.domain.events.ingestion import ingest_dodo_payload
from app.integrations.dodo.client import get_dodo_provider

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class SimulatePaymentRequest(BaseModel):
    amount: float
    currency: str = "USD"
    invoice_reference: str
    customer_reference: str = ""


@router.post("/dodo")
async def dodo_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    provider = get_dodo_provider()
    raw_body = await request.body()
    signature = request.headers.get("webhook-signature")

    if not provider.verify_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    payload = provider.parse_event(raw_body)
    result = ingest_dodo_payload(db, payload, source_mode=provider.mode)
    return result


@router.post("/dodo/simulate")
def simulate_dodo_payment(body: SimulatePaymentRequest, db: Session = Depends(get_db)) -> dict:
    """Fires a locally-generated Dodo-shaped payment event through the exact
    same ingestion pipeline a real webhook uses. Always tagged SIMULATED."""
    from app.integrations.dodo.mock import MockDodoProvider

    provider = MockDodoProvider()
    payload = provider.simulate_payment(
        amount=body.amount,
        currency=body.currency,
        invoice_reference=body.invoice_reference,
        customer_reference=body.customer_reference,
    )
    result = ingest_dodo_payload(db, payload, source_mode="SIMULATED")
    return result
