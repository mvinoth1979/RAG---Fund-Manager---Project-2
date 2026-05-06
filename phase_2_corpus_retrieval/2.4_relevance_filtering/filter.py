"""
Phase 2.4: Relevance Filtering
===============================
Hard threshold filter: discard all chunks below similarity 0.75.
Enforcement: No "best effort" retrieval; all chunks below threshold discarded.
"""

from typing import List
import sys
from pathlib import Path

# Import RetrievalCandidate from hybrid retrieval
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Import the RetrievalCandidate model
try:
    from phase_2_corpus_retrieval.two_dot_3_hybrid_retrieval.hybrid import RetrievalCandidate
except ImportError:
    # Fallback if the exact path doesn't work
    try:
        sys.path.append(str(PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.3_hybrid_retrieval"))
        from hybrid import RetrievalCandidate
    except ImportError:
        # Define locally if import fails
        from pydantic import BaseModel
        
        class RetrievalCandidate(BaseModel):
            chunk_id: str
            doc_id: str
            source_url: str
            chunk_type: str
            text: str
            similarity: float
            rank: int
            retriever: str


class RelevanceFilter:
    THRESHOLD = 0.75

    def filter(self, candidates: List[RetrievalCandidate]) -> List[RetrievalCandidate]:
        """
        Return only candidates with similarity >= THRESHOLD.
        """
        passed = [c for c in candidates if c.similarity >= self.THRESHOLD]
        # Re-rank after filtering
        passed.sort(key=lambda x: -x.similarity)
        for idx, c in enumerate(passed, start=1):
            c.rank = idx
        return passed


def run_relevance_filter(candidates: List[RetrievalCandidate]) -> List[RetrievalCandidate]:
    """Convenience entry-point."""
    return RelevanceFilter().filter(candidates)


if __name__ == "__main__":
    demo = [
        RetrievalCandidate(chunk_id="c1", doc_id="DOC-001", source_url="", chunk_type="expense_ratio", text="...", similarity=0.82, rank=0, retriever="dense"),
        RetrievalCandidate(chunk_id="c2", doc_id="DOC-001", source_url="", chunk_type="exit_load", text="...", similarity=0.71, rank=0, retriever="bm25"),
        RetrievalCandidate(chunk_id="c3", doc_id="DOC-002", source_url="", chunk_type="nav", text="...", similarity=0.91, rank=0, retriever="structured"),
    ]
    result = run_relevance_filter(demo)
    print(f"Before: {len(demo)}  After: {len(result)}")
    for r in result:
        print(f"  rank={r.rank} sim={r.similarity} {r.chunk_id}")
