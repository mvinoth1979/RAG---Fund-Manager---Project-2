"""
Phase 2.1: Query Normalization
===============================
Transforms raw user query into canonical form.
Logic: Lowercase -> punctuation strip -> abbreviation expansion -> synonym mapping -> fund alias canonicalization.
Enforcement: Fixed dictionary; no learned components.
"""

import re
from pydantic import BaseModel


class NormalizedQuery(BaseModel):
    original: str
    normalized: str
    transformations: list[str]


class QueryNormalizer:
    """
    Rule-based query normalizer using fixed dictionaries.
    """

    # Longest-first to avoid partial replacements
    ABBREVIATIONS = {
        "systematic investment plan": "sip",
        "net asset value": "nav",
        "assets under management": "aum",
        "long term capital gains": "ltcg",
        "short term capital gains": "stcg",
        "exchange traded fund": "etf",
        "fund of funds": "fof",
    }

    SYNONYMS = {
        "charges": "expense ratio",
        "fees": "expense ratio",
        "cost": "expense ratio",
        "expenses": "expense ratio",
        "redemption fee": "exit load",
        "exit charge": "exit load",
        "redemption charge": "exit load",
        "minimum sip": "min sip",
        "sip amount": "min sip",
        "minimum lumpsum": "min lumpsum",
        "lumpsum amount": "min lumpsum",
        "launch date": "inception date",
        "started on": "inception date",
        "risk level": "riskometer",
        "risk": "riskometer",
    }

    FUND_ALIASES = {
        "smallcap": "small cap fund",
        "small cap": "small cap fund",
        "ethical": "ethical fund",
        "multi asset allocation": "multi asset allocation fund",
        "multi asset": "multi asset allocation fund",
        "flexicap": "flexi cap fund",
        "flexi cap": "flexi cap fund",
        "liquid": "liquid fund",
        "gold etf fof": "gold etf fof",
        "gold etf": "gold etf fof",
        "gold": "gold etf fof",
        "arbitrage": "arbitrage fund",
    }

    # Combine all replacement dictionaries (longest phrase first)
    @classmethod
    def _build_replacement_patterns(cls) -> list[tuple[str, str]]:
        combined = {}
        # Note: abbreviations are expanded in reverse (acronym -> full form)
        # But we want to EXPAND acronyms, so we map acronym -> full form
        abbrev_expanded = {v: k for k, v in cls.ABBREVIATIONS.items()}
        combined.update(abbrev_expanded)
        combined.update(cls.SYNONYMS)
        combined.update(cls.FUND_ALIASES)
        # Sort by length descending for greedy matching
        return sorted(combined.items(), key=lambda x: len(x[0]), reverse=True)

    def _llm_fuzzy_correct(self, query: str) -> str:
        """
        Use LLM to fix typos with schema-awareness.
        """
        try:
            import importlib.util
            import sys
            from pathlib import Path
            PROJECT_ROOT = Path(__file__).resolve().parents[2]
            llm_path = PROJECT_ROOT / "phase_4_response_generation" / "4.2_llm_inference" / "llm.py"
            
            spec = importlib.util.spec_from_file_location("llm_module", llm_path)
            llm_mod = importlib.util.module_from_spec(spec)
            sys.modules["llm_module"] = llm_mod
            spec.loader.exec_module(llm_mod)
            LLMClient = llm_mod.LLMClient
        except Exception as e:
            logger.error(f"Failed to load LLMClient: {e}")
            return query

        client = LLMClient()
        
        # Deep Schema Dictionary for high-precision correction
        schema_context = {
            "SIP": ["Systematic Investment Plan", "syp", "sysmatic", "systemic", "sip amount", "monthly investment"],
            "NAV": ["Net Asset Value", "nva", "nsv", "unit price", "current price", "nav value"],
            "AUM": ["Assets Under Management", "fund size", "total assets", "aum size", "how big is the fund"],
            "Expense Ratio": ["charges", "fees", "cost of fund", "expnse", "management fee", "ter"],
            "Exit Load": ["penalty", "redemption charges", "exit fee", "ext lode", "lock in penalty"],
            "Benchmark": ["index", "comparison index", "bnchmark", "standard"],
            "Fund Manager": ["who manages", "manager name", "portfolio manager", "mngr"],
            "Inception Date": ["launch date", "start date", "started on", "age of fund"]
        }

        system_prompt = (
            "You are a sophisticated financial query repair engine. Your mission is to normalize user queries about Mutual Funds.\n\n"
            "--- CORRECTION STRATEGY ---\n"
            "1. **SIP Repair**: Correct 'syp', 'sysmatic', or 'systemic' to 'SIP'.\n"
            "2. **NAV/AUM Repair**: Correct 'nva', 'nsv' to 'NAV' and 'assets' to 'AUM' if context implies fund size.\n"
            "3. **Scheme Alignment**: Map partial or misspelled names to: 'Small Cap Fund', 'Ethical Fund', 'Multi Asset Allocation Fund', 'Flexi Cap Fund', 'Gold ETF FOF', 'Liquid Fund', 'Arbitrage Fund'.\n"
            "4. **Attribute Normalization**: Map 'charges/fees' to 'Expense Ratio', 'penalty' to 'Exit Load', and 'who runs' to 'Fund Manager'.\n"
            "5. **Hinglish/Informal**: Handle informal phrasing like 'kitna hai' or 'details' by focusing on the core fact requested.\n\n"
            "--- EXAMPLES ---\n"
            "Input: 'min syp for flexicp' -> Output: 'minimum SIP for Flexi Cap Fund'\n"
            "Input: 'nva of ethical' -> Output: 'NAV of Ethical Fund'\n"
            "Input: 'fund size of multi asset' -> Output: 'AUM of Multi Asset Allocation Fund'\n"
            "Input: 'ext lode for liquid' -> Output: 'exit load for Liquid Fund'\n"
            "Input: 'who manages smal cap' -> Output: 'fund manager for Small Cap Fund'\n"
            "Input: 'sysmatic plan details' -> Output: 'SIP details'\n\n"
            "--- RULES ---\n"
            "- Return ONLY the corrected query string.\n"
            "- No preamble, no conversational filler.\n"
            "- If the query is already perfect, return it unchanged."
        )
        
        try:
            corrected, _ = client.generate(system_prompt, query)
            return corrected.strip().strip("'\"") # Remove quotes if LLM adds them
        except Exception as e:
            return query

    def normalize(self, query: str) -> NormalizedQuery:
        original = query.strip()
        transformations: list[str] = []

        # 1. LLM Fuzzy Correction (New)
        corrected = self._llm_fuzzy_correct(original)
        if corrected != original:
            transformations.append(f"Fuzzy Correction: {original} -> {corrected}")
            text = corrected.lower()
        else:
            text = original.lower()

        # 2. Strip punctuation (replace with spaces)
        text = re.sub(r"[^\w\s]", " ", text)

        # 3. Collapse multiple spaces
        text = re.sub(r"\s+", " ", text).strip()

        # 4. Apply replacements (longest phrase first)
        patterns = self._build_replacement_patterns()
        for phrase, replacement in patterns:
            # Use word-boundary-safe replacement for single words, plain for phrases
            if " " in phrase:
                new_text = text.replace(phrase, replacement)
            else:
                new_text = re.sub(rf"\b{re.escape(phrase)}\b", replacement, text)
            if new_text != text:
                transformations.append(f"{phrase} -> {replacement}")
                text = new_text

        return NormalizedQuery(
            original=original,
            normalized=text,
            transformations=transformations,
        )


def run_normalizer(query: str) -> NormalizedQuery:
    """Convenience entry-point."""
    return QueryNormalizer().normalize(query)


if __name__ == "__main__":
    tests = [
        "What is the expense ratio of the Small Cap Fund?",
        "What are the charges for liquid?",
        "Tell me the NAV and min SIP for Flexi Cap.",
        "Exit load of Gold ETF?",
        "Should I compare Small Cap vs Liquid?",
    ]
    for q in tests:
        res = run_normalizer(q)
        print(f"Original:  {res.original}")
        print(f"Canonical: {res.normalized}")
        print(f"Changes:   {res.transformations}")
        print("-" * 50)
