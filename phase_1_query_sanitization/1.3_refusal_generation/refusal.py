"""
Phase 1.3: Refusal Generation
==============================
Assembles terminal response T2 for ADVISORY or UNCLEAR intent.
Enforcement: No LLM called; pre-approved template injection.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel

# =============================================================================
# Data Models
# =============================================================================


class RefusalResponse(BaseModel):
    type: str = "refusal"
    text: str
    source_url: Optional[str] = None
    footer_date: str


# =============================================================================
# Refusal Generator
# =============================================================================


class RefusalGenerator:
    """
    Generates the T2 refusal response for advisory or unclear queries.
    """

    T2_TEMPLATE = (
        "I can only share factual information from official sources.\n"
        "I cannot provide investment advice or recommendations.\n\n"
        "You can learn more about mutual fund basics here:\n"
        "https://www.amfiindia.com/investor-corner/knowledge-center.html\n\n"
        "Source: N/A\n"
        "Last updated from sources: {date}"
    )

    def generate(self, classification: str) -> RefusalResponse:
        """
        Generate T2 refusal if intent is ADVISORY or UNCLEAR.
        Raises ValueError if intent is FACTUAL (should not reach refusal gate).
        """
        if classification == "FACTUAL":
            raise ValueError(
                "Refusal gate should not be called with FACTUAL intent. "
                "Route to retrieval instead."
            )

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return RefusalResponse(
            type="refusal",
            text=self.T2_TEMPLATE.format(date=today),
            source_url=None,
            footer_date=today,
        )


def run_refusal_gate(classification: str) -> RefusalResponse:
    """Convenience entry-point for the refusal gate."""
    generator = RefusalGenerator()
    return generator.generate(classification)


if __name__ == "__main__":
    for cls in ("ADVISORY", "UNCLEAR", "FACTUAL"):
        try:
            refusal = run_refusal_gate(cls)
            print(f"[REFUSAL for {cls}]")
            print(refusal.text)
            print("-" * 40)
        except ValueError as e:
            print(f"[SKIP {cls}] {e}")
