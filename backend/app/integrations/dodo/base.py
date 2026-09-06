from abc import ABC, abstractmethod


class DodoProvider(ABC):
    """Adapter interface for Dodo Payments.

    Three modes, never conflated in the UI or a proof capsule:
      LIVE      — real API key + webhook secret; inbound signatures verified.
      SANDBOX   — real Dodo test-mode API key, no webhook secret; outbound
                  reads against test.dodopayments.com are real, but inbound
                  webhook signatures cannot be cryptographically verified.
      SIMULATED — no credentials; everything is a local fabrication.
    """

    mode: str  # "LIVE" | "SANDBOX" | "SIMULATED"

    @abstractmethod
    def verify_signature(self, payload: bytes, signature_header: str | None) -> bool: ...

    @abstractmethod
    def parse_event(self, payload: bytes) -> dict: ...

    @abstractmethod
    def simulate_payment(self, *, amount: float, currency: str, invoice_reference: str, customer_reference: str) -> dict:
        """Build a synthetic Dodo-shaped webhook payload for demo/testing."""
        ...

    def get_real_payment(self, payment_id: str) -> dict | None:
        """Look up a real payment by id against the live/sandbox Dodo API.
        Returns None if this provider has no real API access (SIMULATED) or
        the payment doesn't exist. Never fabricates a result."""
        return None
