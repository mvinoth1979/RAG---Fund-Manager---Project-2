import sys
import sqlite3
from pathlib import Path
import logging

logging.basicConfig(level=logging.WARNING)

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports from phases
from phase_1_query_sanitization.phase_1_runner import run_phase_1
from phase_2_corpus_retrieval.phase_2_orchestrator import run_phase_2_retrieval
from phase_3_context_assembly.pipeline import ContextAssemblyPipeline
from phase_3_context_assembly.models import Chunk

def get_whitelist():
    db_path = PROJECT_ROOT / "data" / "5_structured_facts" / "facts.db"
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT source_url FROM structured_facts")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Failed to load whitelist: {e}")
        return []

def run_integration():
    test_queries = [
        "What is the expense ratio of the Small Cap Fund?",
        "Tell me about the exit load for the Liquid Fund.",
        "Should I invest my money in the Flexi Cap Fund?",
        "My PAN is ABCD1234E, what is the NAV?"
    ]

    whitelist = get_whitelist()
    print(f"Loaded {len(whitelist)} whitelisted URLs.")

    pipeline_phase_3 = ContextAssemblyPipeline(whitelist=whitelist, max_tokens=2000)

    for q in test_queries:
        print("\n" + "="*80)
        print(f"QUERY: '{q}'")
        print("="*80)

        # PHASE 1
        p1_result = run_phase_1(q)
        if p1_result["blocked_by_pii"]:
            print(f"[PHASE 1] Blocked by PII. Terminal State T1.")
            print(f"Response: {p1_result['terminal_response']['text']}")
            continue
        elif p1_result["terminal_response"]:
            print(f"[PHASE 1] Advisory Intent Detected. Terminal State T2.")
            print(f"Response: {p1_result['terminal_response']['text']}")
            continue
        
        sanitized_query = p1_result["sanitized_query"]
        print(f"[PHASE 1] Passed! Sanitized query: '{sanitized_query}'")

        # PHASE 2
        p2_result = run_phase_2_retrieval(sanitized_query)
        if p2_result.advisory_triggered:
            print(f"[PHASE 2] Advisory triggered during resolution: {p2_result.advisory_reason}")
            continue
            
        candidates = p2_result.filtered_candidates
        print(f"[PHASE 2] Retrieved {len(candidates)} relevant candidates.")
        if not candidates:
            print("[PHASE 2] No candidates found. Terminal State T3.")
            continue

        # Map to Phase 3 Chunk model
        phase_3_chunks = []
        for c in candidates:
            phase_3_chunks.append(Chunk(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                source_url=c.source_url,
                chunk_type=c.chunk_type,
                text=c.text
            ))

        # PHASE 3
        context_string, source_url, doc_id = pipeline_phase_3.execute(phase_3_chunks)
        
        print("[PHASE 3] Assembly Successful!")
        print(f"  Selected Source URL : {source_url}")
        print(f"  Selected Doc ID     : {doc_id}")
        print(f"  Assembled Context   : {context_string[:200]}...")

if __name__ == "__main__":
    run_integration()
