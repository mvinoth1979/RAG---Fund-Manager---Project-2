import sys
import os
import sqlite3
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.WARNING)

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Imports from phases
from phase_1_query_sanitization.phase_1_runner import run_phase_1
from phase_2_corpus_retrieval.phase_2_orchestrator import run_phase_2
from phase_3_context_assembly.pipeline import ContextAssemblyPipeline
from phase_3_context_assembly.models import Chunk
from phase_4_response_generation.generator import ResponseGenerator
from phase_5_compliance_validation.pipeline import CompliancePipeline

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
        "Should I invest my money in the Flexi Cap Fund?"
    ]

    whitelist = get_whitelist()
    print(f"Loaded {len(whitelist)} whitelisted URLs.")

    pipeline_phase_3 = ContextAssemblyPipeline(whitelist=whitelist, max_tokens=2000)
    generator_phase_4 = ResponseGenerator()
    
    banned_phrases_path = os.getenv("BANNED_PHRASES_PATH", "./phase_5_compliance_validation/5.1_advisory_detection/banned_phrases.json")
    banned_phrases_path = os.path.join(PROJECT_ROOT, banned_phrases_path.replace("./", ""))
    pipeline_phase_5 = CompliancePipeline(banned_phrases_path=banned_phrases_path)

    for q in test_queries:
        print("\n" + "="*80)
        print(f"QUERY: '{q}'")
        print("="*80)

        # PHASE 1
        p1_result = run_phase_1(q)
        if p1_result["blocked_by_pii"] or p1_result["terminal_response"]:
            print(f"[PHASE 1] Blocked/Advisory. Terminal State.")
            continue
        
        sanitized_query = p1_result["sanitized_query"]
        print(f"[PHASE 1] Passed! Sanitized query: '{sanitized_query}'")

        # PHASE 2
        p2_result = run_phase_2(sanitized_query)
        if p2_result.advisory_triggered:
            continue
            
        candidates = p2_result.filtered_candidates
        print(f"[PHASE 2] Retrieved {len(candidates)} relevant candidates.")
        if not candidates:
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

        # PHASE 4
        print("[PHASE 4] Generating Response via LLM...")
        p4_response = generator_phase_4.generate_response(context_string, sanitized_query)
        
        print(f"[PHASE 4] Generation Complete! Status: {p4_response.status}")
        if p4_response.status != "SUCCESS":
            print(f"  -> Error Response: {p4_response.text}")
            continue

        # PHASE 5
        print("[PHASE 5] Validating Compliance...")
        p5_result = pipeline_phase_5.validate(
            raw_response=p4_response.text,
            source_context=context_string,
            source_url=source_url
        )

        print(f"[PHASE 5] Validation Status: {p5_result.status}")
        if p5_result.violations:
            print(f"  -> Violations found: {p5_result.violations}")
            
        print("\n=== FINAL DELIVERABLE RESPONSE ===")
        print(p5_result.response)
        print("===================================\n")

if __name__ == "__main__":
    run_integration()
