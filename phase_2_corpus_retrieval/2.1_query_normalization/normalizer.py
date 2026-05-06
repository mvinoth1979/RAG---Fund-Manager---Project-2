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
        
        # Schema awareness lists
        funds = ["Small Cap Fund", "Ethical Fund", "Multi Asset Allocation Fund", "Flexi Cap Fund", "Gold ETF FOF", "Liquid Fund", "Arbitrage Fund"]
        facts = ["NAV (Net Asset Value)", "AUM (Assets Under Management)", "Expense Ratio (Charges/Fees)", "Exit Load", "Min SIP", "Min Lumpsum", "Benchmark", "Riskometer (Risk Level)", "Fund Manager", "Inception Date (Launch Date)"]

        system_prompt = (
            "You are a high-precision typo correction engine for a Mutual Fund FAQ system.\n"
            "Your goal is to repair user queries containing misspellings, letter transpositions, or ambiguous abbreviations.\n\n"
            "--- VALID SCHEMA ---\n"
            f"SUPPORTED FUNDS: {', '.join(funds)}\n"
            f"SUPPORTED FACTS: {', '.join(facts)}\n\n"
            "--- CORRECTION RULES ---\n"
            "1. Fix letter transpositions (e.g., 'NVA' -> 'NAV', 'NSV' -> 'NAV').\n"
            "2. Fix phonetic misspellings (e.g., 'Smal' -> 'Small', 'Flexicp' -> 'Flexi Cap').\n"
            "3. Map synonyms to canonical terms (e.g., 'cost' -> 'expense ratio', 'started on' -> 'inception date').\n"
            "4. Preserve the overall intent of the question.\n"
            "5. If no correction is needed, return the original query exactly.\n"
            "6. Respond ONLY with the corrected query string. No preamble, no explanation.\n\n"
            "--- EXAMPLES ---\n"
            "Input: 'What is the nva of smal cap?' -> Output: 'What is the NAV of Small Cap Fund?'\n"
            "Input: 'expnse for flexicp' -> Output: 'expense ratio for Flexi Cap Fund'\n"
            "Input: 'min sip for liquid' -> Output: 'min SIP for Liquid Fund'\n"
            "Input: 'Who is the manager for ethical?' -> Output: 'Who is the fund manager for Ethical Fund?'"
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
