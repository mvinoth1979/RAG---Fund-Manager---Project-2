"""
Phase 1: Query Sanitization & Classification (Online)
======================================================
End-to-end runner that chains:
  1.1 PII Detection -> 1.2 Intent Classification -> 1.3 Refusal Generation

Enforcement:
- PII match -> immediate T1 terminal state; query never proceeds.
- ADVISORY/UNCLEAR intent -> T2 refusal template; no LLM called.
- FACTUAL intent -> sanitized query passed to Phase 2 retrieval.
"""

import sys
from pathlib import Path

# Add project root to path so sub-phase scripts can be found
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import gates via importlib because directory names contain dots/numbers
import importlib.util


def _load_module(module_path: Path):
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load sub-phase modules
pii_mod = _load_module(
    PROJECT_ROOT / "phase_1_query_sanitization" / "1.1_pii_detection" / "pii.py"
)
intent_mod = _load_module(
    PROJECT_ROOT / "phase_1_query_sanitization" / "1.2_intent_classification" / "intent.py"
)
refusal_mod = _load_module(
    PROJECT_ROOT / "phase_1_query_sanitization" / "1.3_refusal_generation" / "refusal.py"
)

# Extract convenience functions
run_pii_gate = pii_mod.run_pii_gate
run_intent_gate = intent_mod.run_intent_gate
run_refusal_gate = refusal_mod.run_refusal_gate


def run_phase_1(query: str):
    """
    Execute full Phase 1 pipeline on a raw user query.
    Returns a dict with the outcome and any terminal response.
    """
    result = {
        "query": query,
        "blocked_by_pii": False,
        "sanitized_query": None,
        "intent": None,
        "terminal_response": None,
        "next_phase": None,
    }

    # ------------------------------------------------------------------
    # 1.1 PII Detection
    # ------------------------------------------------------------------
    pii_result = run_pii_gate(query)
    result["sanitized_query"] = pii_result.query

    if pii_result.blocked:
        result["blocked_by_pii"] = True
        result["terminal_response"] = {
            "type": "refusal",
            "text": pii_result.response_text,
            "source_url": pii_result.source_url,
            "footer_date": pii_result.footer_date,
            "terminal_state": "T1",
        }
        result["next_phase"] = None
        return result

    # ------------------------------------------------------------------
    # 1.2 Intent Classification
    # ------------------------------------------------------------------
    intent_result = run_intent_gate(pii_result.query)
    result["intent"] = {
        "classification": intent_result.classification,
        "advisory_score": intent_result.advisory_score,
        "triggers_matched": intent_result.triggers_matched,
    }

    # ------------------------------------------------------------------
    # 1.3 Refusal Generation (if not factual)
    # ------------------------------------------------------------------
    if intent_result.classification in ("ADVISORY", "UNCLEAR"):
        refusal = run_refusal_gate(intent_result.classification)
        result["terminal_response"] = {
            "type": "refusal",
            "text": refusal.text,
            "source_url": refusal.source_url,
            "footer_date": refusal.footer_date,
            "terminal_state": "T2",
        }
        result["next_phase"] = None
        return result

    # ------------------------------------------------------------------
    # FACTUAL -> proceed to Phase 2
    # ------------------------------------------------------------------
    result["next_phase"] = "phase_2_corpus_retrieval"
    return result


def main():
    test_queries = [
        # Factual queries
        "What is the expense ratio of the Small Cap Fund?",
        "What is the minimum SIP amount for the Liquid Fund?",
        "What is the benchmark for the Flexi Cap Fund?",
        "Tell me the exit load.",
        # Advisory queries
        "Should I invest in the Small Cap Fund?",
        "Is the Liquid Fund safe?",
        "Buy this fund now",
        "Which fund is better?",
        # PII queries
        "My PAN is ABCDE1234F, what fund should I buy?",
        "Call me at 9876543210 about the expense ratio",
        "Email me at user@example.com",
        # Unclear
        "Tell me about returns",
        "Funds",
    ]

    print("=" * 70)
    print("PHASE 1: QUERY SANITIZATION & CLASSIFICATION")
    print("=" * 70)

    stats = {"T1": 0, "T2": 0, "FACTUAL": 0, "UNCLEAR": 0}

    for q in test_queries:
        res = run_phase_1(q)
        print(f"\nQuery: {q}")

        if res["blocked_by_pii"]:
            print(f"  -> [T1 BLOCKED] PII detected: {res['terminal_response']['text'].split(chr(10))[0]}")
            stats["T1"] += 1
        elif res["terminal_response"]:
            print(f"  -> [T2 REFUSAL] Intent={res['intent']['classification']} score={res['intent']['advisory_score']}")
            print(f"     Response: {res['terminal_response']['text'].split(chr(10))[0]}")
            stats["T2"] += 1
        else:
            print(f"  -> [FACTUAL] Intent={res['intent']['classification']} score={res['intent']['advisory_score']}")
            print(f"  -> Next: {res['next_phase']}")
            stats["FACTUAL"] += 1

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  T1 (PII blocked):     {stats['T1']}")
    print(f"  T2 (Advisory refused): {stats['T2']}")
    print(f"  FACTUAL (proceed):    {stats['FACTUAL']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
