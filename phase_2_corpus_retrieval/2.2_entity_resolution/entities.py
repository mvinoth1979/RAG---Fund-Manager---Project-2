import re
from typing import Optional
from pydantic import BaseModel

class ResolvedQuery(BaseModel):
    original_query: str
    normalized_query: str
    mentioned_funds: list[str]
    fund_resolution_confidence: float
    fact_type: Optional[str]
    fact_confidence: float
    is_ambiguous: bool
    advisory_trigger: bool = False
    advisory_reason: str = ""

class EntityResolver:
    FUND_MAP = {
        "small cap fund": "DOC-001",
        "small cap": "DOC-001",
        "smallcap": "DOC-001",
        "ethical fund": "DOC-002",
        "ethical": "DOC-002",
        "multi asset allocation fund": "DOC-003",
        "multi asset allocation": "DOC-003",
        "multi asset": "DOC-003",
        "flexi cap fund": "DOC-004",
        "flexi cap": "DOC-004",
        "flexicap": "DOC-004",
        "liquid fund": "DOC-006",
        "liquid": "DOC-006",
        "gold etf fof": "DOC-005",
        "gold etf": "DOC-005",
        "gold": "DOC-005",
        "arbitrage fund": "DOC-007",
        "arbitrage": "DOC-007",
    }

    DOC_ID_TO_URL = {
        "DOC-001": "https://groww.in/mutual-funds/the-wealth-company-small-cap-fund-direct-growth",
        "DOC-002": "https://groww.in/mutual-funds/the-wealth-company-ethical-fund-direct-growth",
        "DOC-003": "https://groww.in/mutual-funds/the-wealth-company-multi-asset-allocation-fund-direct-growth",
        "DOC-004": "https://groww.in/mutual-funds/the-wealth-company-flexi-cap-fund-direct-growth",
        "DOC-005": "https://groww.in/mutual-funds/the-wealth-company-gold-etf-fof-direct-growth",
        "DOC-006": "https://groww.in/mutual-funds/the-wealth-company-liquid-fund-direct-growth",
        "DOC-007": "https://groww.in/mutual-funds/the-wealth-company-arbitrage-fund-direct-growth",
    }

    FACT_MAP = {
        "expense ratio": "expense_ratio",
        "charges": "expense_ratio",
        "fees": "expense_ratio",
        "cost": "expense_ratio",
        "exit load": "exit_load",
        "redemption fee": "exit_load",
        "exit charge": "exit_load",
        "min sip": "min_sip",
        "minimum sip": "min_sip",
        "systematic investment plan": "min_sip",
        "sip amount": "min_sip",
        "min lumpsum": "min_lumpsum",
        "minimum lumpsum": "min_lumpsum",
        "lumpsum amount": "min_lumpsum",
        "benchmark": "benchmark",
        "nav": "nav",
        "net asset value": "nav",
        "aum": "aum",
        "assets under management": "aum",
        "asset under management": "aum",
        "fund size": "aum",
        "riskometer": "risk_level",
        "risk level": "risk_level",
        "risk": "risk_level",
        "fund manager": "fund_manager",
        "manager": "fund_manager",
        "inception date": "inception_date",
        "launch date": "inception_date",
        "category": "category",
        "tax": "tax",
        "taxation": "tax",
        "holdings": "holdings",
        "portfolio": "holdings",
        "investment objective": "investment_objective",
        "objective": "investment_objective",
        "overview": "overview",
        "total aum": "total_aum",
    }

    COMPARISON_WORDS = [
        "better", "worse", "superior", "inferior", "compare",
        "comparison", "versus", "vs", "difference", "diff",
    ]

    def resolve(self, original_query: str, normalized_query: str) -> ResolvedQuery:
        text = normalized_query.lower()
        mentioned_funds: list[str] = []
        for alias, doc_id in self.FUND_MAP.items():
            if alias in text and doc_id not in mentioned_funds:
                mentioned_funds.append(doc_id)

        if len(mentioned_funds) == 1:
            fund_confidence = 1.0
        elif len(mentioned_funds) > 1:
            fund_confidence = 1.0
        else:
            fund_confidence = 0.0

        fact_type: Optional[str] = None
        fact_confidence = 0.0
        
        # Sort keys by length descending to match longest phrase first
        sorted_keys = sorted(self.FACT_MAP.keys(), key=len, reverse=True)
        for alias in sorted_keys:
            if alias in text:
                fact_type = self.FACT_MAP[alias]
                fact_confidence = 1.0
                break

        has_comparison = any(word in text for word in self.COMPARISON_WORDS)
        
        # Ambiguity Case 1: Multiple funds with comparison
        is_ambiguous_comparison = len(mentioned_funds) > 1 and has_comparison
        
        # Ambiguity Case 2: Fact requested but no fund mentioned
        is_missing_fund = fact_type is not None and len(mentioned_funds) == 0
        
        is_ambiguous = is_ambiguous_comparison or is_missing_fund

        advisory_trigger = is_ambiguous
        advisory_reason = ""
        if is_ambiguous_comparison:
            advisory_reason = (
                "Multiple fund mentions with explicit comparison detected. "
                "Advisory refusal triggered per architecture enforcement."
            )
        elif is_missing_fund:
            advisory_reason = (
                f"The query asks for '{fact_type}' but does not specify a mutual fund. "
                "Ambiguous query handling triggered."
            )

        return ResolvedQuery(
            original_query=original_query,
            normalized_query=normalized_query,
            mentioned_funds=mentioned_funds,
            fund_resolution_confidence=fund_confidence,
            fact_type=fact_type,
            fact_confidence=fact_confidence,
            is_ambiguous=is_ambiguous,
            advisory_trigger=advisory_trigger,
            advisory_reason=advisory_reason,
        )

def run_entity_resolver(original_query: str, normalized_query: str) -> ResolvedQuery:
    return EntityResolver().resolve(original_query, normalized_query)
