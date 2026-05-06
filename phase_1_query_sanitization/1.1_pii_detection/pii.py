"""
Phase 1.1: PII Detection
========================
Regex-based PII scanner for user queries.
Enforcement: Any match -> immediate terminal state T1; query never reaches LLM.
"""

import re
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Data Models
# =============================================================================


class PIIDetectionResult(BaseModel):
    blocked: bool
    query: str = Field(..., max_length=200)
    violations: List[str] = Field(default_factory=list)
    terminal_state: Optional[Literal["T1"]] = None
    response_text: str = ""
    source_url: Optional[str] = None
    footer_date: str = ""


# =============================================================================
# PII Detector
# =============================================================================


class PIIDetector:
    """
    Scans user queries for Indian PII patterns.
    Patterns: PAN, Aadhaar, bank account numbers, OTP, email, phone.
    """

    PATTERNS = {
        "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
        "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
        "ACCOUNT_NUMBER": re.compile(r"\b\d{9,18}\b"),
        "OTP": re.compile(r"(?i)\botp\b[:\s-]*\d{4,6}|\d{4,6}[:\s-]*\botp\b"),
        "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "PHONE": re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b"),
    }

    T1_TEMPLATE = (
        "I cannot process personal or sensitive information.\n"
        "Please ask factual questions about mutual fund schemes.\n\n"
        "Source: N/A\n"
        "Last updated from sources: {date}"
    )

    def scan(self, query: str) -> PIIDetectionResult:
        """
        Scan a raw query for PII.
        Returns PIIDetectionResult with blocked=True if any PII found.
        """
        violations: List[str] = []

        for pii_type, pattern in self.PATTERNS.items():
            if pattern.search(query):
                violations.append(pii_type)

        if violations:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return PIIDetectionResult(
                blocked=True,
                query=query,
                violations=violations,
                terminal_state="T1",
                response_text=self.T1_TEMPLATE.format(date=today),
                source_url=None,
                footer_date=today,
            )

        return PIIDetectionResult(
            blocked=False,
            query=query,
            violations=[],
        )

    def sanitize(self, query: str) -> str:
        """
        Strip leading/trailing whitespace and enforce max length.
        Returns sanitized query string.
        """
        sanitized = query.strip()
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized


def run_pii_gate(query: str) -> PIIDetectionResult:
    """
    Convenience entry-point for the PII gate.
    1. Sanitize input
    2. Scan for PII
    3. Return result (blocked or clean)
    """
    detector = PIIDetector()
    clean_query = detector.sanitize(query)
    result = detector.scan(clean_query)
    result.query = clean_query
    return result


if __name__ == "__main__":
    # Quick self-test
    test_queries = [
        "What is the expense ratio?",
        "My PAN is ABCDE1234F",
        "Call me at 9876543210",
        "Email me at user@example.com",
        "My aadhaar is 1234 5678 9012",
        "OTP is 123456",
        "Account number 1234567890",
    ]

    for q in test_queries:
        res = run_pii_gate(q)
        status = "BLOCKED" if res.blocked else "CLEAN"
        print(f"[{status}] {q[:50]}... violations={res.violations}")
