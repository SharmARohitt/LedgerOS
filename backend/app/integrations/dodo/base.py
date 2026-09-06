from abc import ABC, abstractmethod


class DodoProvider(ABC):
    """Adapter interface for Dodo Payments. A real provider verifies webhook
    signatures against DODO_WEBHOOK_SECRET; the mock provider always accepts
    but tags every event source_mode=SIMULATED so it can never be confused
    with a live payment in the UI or in a proof capsule."""

    mode: str  # "LIVE" | "SIMULATED"

    @abstractmethod
    def verify_signature(self, payload: bytes, signature_header: str | None) -> bool: ...

    @abstractmethod
    def parse_event(self, payload: bytes) -> dict: ...

    @abstractmethod
    def simulate_payment(self, *, amount: float, currency: str, invoice_reference: str, customer_reference: str) -> dict:
        """Build a synthetic Dodo-shaped webhook payload for demo/testing."""
        ...
