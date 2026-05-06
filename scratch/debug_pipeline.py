import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv()

from phase_1_query_sanitization.phase_1_runner import run_phase_1
from phase_2_corpus_retrieval.phase_2_orchestrator import run_phase_2_retrieval
from phase_3_context_assembly.pipeline import ContextAssemblyPipeline
from phase_3_context_assembly.models import Chunk
from phase_4_response_generation.generator import ResponseGenerator
import sqlite3

def get_whitelist():
    db_path = PROJECT_ROOT / "data" / "5_structured_facts" / "facts.db"
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT source_url FROM structured_facts")
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []

query = "What is the expense ratio of the Small Cap Fund?"
print(f"Query: {query}\n")

# Phase 1
p1_result = run_phase_1(query)
print(f"Phase 1 - Sanitized: {p1_result['sanitized_query']}")

# Phase 2
p2_result = run_phase_2_retrieval(p1_result['sanitized_query'])
print(f"Phase 2 - Found {len(p2_result.filtered_candidates)} candidates")
for i, c in enumerate(p2_result.filtered_candidates[:3]):
    print(f"  [{i}] Doc: {c.doc_id}, Score: {c.similarity:.4f}, Type: {c.chunk_type}")
    print(f"      Snippet: {c.text[:100]}...")

# Phase 3
whitelist = get_whitelist()
pipeline_phase_3 = ContextAssemblyPipeline(whitelist=whitelist, max_tokens=2000)
phase_3_chunks = [Chunk(chunk_id=c.chunk_id, doc_id=c.doc_id, source_url=c.source_url, chunk_type=c.chunk_type, text=c.text) for c in p2_result.filtered_candidates]
context_string, source_url, doc_id = pipeline_phase_3.execute(phase_3_chunks)
print(f"\nPhase 3 - Selected Source: {source_url}")
print(f"Context Length: {len(context_string)}")

# Phase 4
generator_phase_4 = ResponseGenerator()
p4_response = generator_phase_4.generate_response(context_string, p1_result['sanitized_query'])
print(f"\nPhase 4 - Status: {p4_response.status}")
print(f"Response: {p4_response.text}")
