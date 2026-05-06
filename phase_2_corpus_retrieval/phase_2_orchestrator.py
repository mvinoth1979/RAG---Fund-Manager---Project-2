"""
Phase 2 Orchestrator
===================
Main entry point for Phase 2: Corpus Retrieval pipeline.
Coordinates: 2.1 Query Normalization -> 2.2 Entity Resolution -> 2.3 Hybrid Retrieval -> 2.4 Relevance Filtering
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Import all Phase 2 components
sys.path.append(str(PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.1_query_normalization"))
sys.path.append(str(PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.2_entity_resolution"))
sys.path.append(str(PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.3_hybrid_retrieval"))
sys.path.append(str(PROJECT_ROOT / "phase_2_corpus_retrieval" / "2.4_relevance_filtering"))

from normalizer import QueryNormalizer, NormalizedQuery
from entities import EntityResolver, ResolvedQuery
from hybrid import HybridRetriever, RetrievalCandidate
from filter import RelevanceFilter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("phase_2_orchestrator")


class Phase2Result:
    """Complete result from Phase 2 pipeline."""
    
    def __init__(
        self,
        original_query: str,
        normalized: NormalizedQuery,
        resolved: ResolvedQuery,
        candidates: List[RetrievalCandidate],
        filtered_candidates: List[RetrievalCandidate],
        advisory_triggered: bool = False,
        advisory_reason: str = ""
    ):
        self.original_query = original_query
        self.normalized = normalized
        self.resolved = resolved
        self.candidates = candidates
        self.filtered_candidates = filtered_candidates
        self.advisory_triggered = advisory_triggered
        self.advisory_reason = advisory_reason
        
    @property
    def has_results(self) -> bool:
        """Check if pipeline produced any filtered results."""
        return len(self.filtered_candidates) > 0
        
    @property
    def top_result(self) -> Optional[RetrievalCandidate]:
        """Get the top filtered result."""
        return self.filtered_candidates[0] if self.filtered_candidates else None


class Phase2Orchestrator:
    """
    Orchestrates the complete Phase 2: Corpus Retrieval pipeline.
    
    Pipeline:
    1. Query Normalization (2.1)
    2. Entity/Scheme Resolution (2.2) 
    3. Hybrid Retrieval (2.3)
    4. Relevance Filtering (2.4)
    """
    
    def __init__(self):
        self.normalizer = QueryNormalizer()
        self.entity_resolver = EntityResolver()
        self.hybrid_retriever = HybridRetriever()
        self.relevance_filter = RelevanceFilter()
        
        logger.info("Phase 2 Orchestrator initialized")
        logger.info(f"  - Query Normalizer: Ready")
        logger.info(f"  - Entity Resolver: Ready")
        logger.info(f"  - Hybrid Retriever: Ready")
        logger.info(f"  - Relevance Filter: Threshold={self.relevance_filter.THRESHOLD}")
    
    def process_query(self, query: str) -> Phase2Result:
        """
        Process a user query through the complete Phase 2 pipeline.
        
        Args:
            query: Raw user query (already sanitized from Phase 1)
            
        Returns:
            Phase2Result with all intermediate and final results
        """
        logger.info(f"Processing query: '{query}'")
        
        # Step 2.1: Query Normalization
        normalized = self.normalizer.normalize(query)
        logger.debug(f"2.1 Normalized: '{normalized.normalized}'")
        logger.debug(f"    Transformations: {normalized.transformations}")
        
        # Step 2.2: Entity Resolution
        resolved = self.entity_resolver.resolve(normalized.original, normalized.normalized)
        logger.debug(f"2.2 Resolved funds: {resolved.mentioned_funds}")
        logger.debug(f"    Fact type: {resolved.fact_type} (confidence: {resolved.fact_confidence})")
        
        # Check for advisory trigger
        if resolved.advisory_trigger:
            logger.warning(f"ADVISORY TRIGGERED: {resolved.advisory_reason}")
            return Phase2Result(
                original_query=query,
                normalized=normalized,
                resolved=resolved,
                candidates=[],
                filtered_candidates=[],
                advisory_triggered=True,
                advisory_reason=resolved.advisory_reason
            )
        
        # Step 2.3: Hybrid Retrieval
        candidates = self.hybrid_retriever.retrieve(
            normalized_query=resolved.normalized_query,
            mentioned_funds=resolved.mentioned_funds,
            fact_type=resolved.fact_type,
            fact_confidence=resolved.fact_confidence
        )
        logger.debug(f"2.3 Retrieved {len(candidates)} candidates")
        
        # Step 2.4: Relevance Filtering
        filtered_candidates = self.relevance_filter.filter(candidates)
        logger.debug(f"2.4 Filtered to {len(filtered_candidates)} candidates")
        
        logger.info(f"Query processed: {len(filtered_candidates)} relevant chunks found")
        
        return Phase2Result(
            original_query=query,
            normalized=normalized,
            resolved=resolved,
            candidates=candidates,
            filtered_candidates=filtered_candidates
        )
    
    def get_summary_stats(self) -> dict:
        """Get summary statistics about the retriever state."""
        try:
            chroma_count = self.hybrid_retriever.collection.count()
            chunks_count = len(self.hybrid_retriever.chunks)
            
            return {
                "chroma_documents": chroma_count,
                "total_chunks": chunks_count,
                "relevance_threshold": self.relevance_filter.THRESHOLD,
                "rrf_k": self.hybrid_retriever.RRF_K,
                "dense_topk": self.hybrid_retriever.DENSE_TOPK,
                "bm25_topk": self.hybrid_retriever.BM25_TOPK
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}


# Global orchestrator instance
_orchestrator: Optional[Phase2Orchestrator] = None


def get_phase_2_orchestrator() -> Phase2Orchestrator:
    """Get or create the global Phase 2 orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Phase2Orchestrator()
    return _orchestrator


def run_phase_2(query: str) -> Phase2Result:
    """
    Convenience function to run Phase 2 retrieval.
    
    Args:
        query: Sanitized user query from Phase 1
        
    Returns:
        Phase2Result with retrieval results
    """
    orchestrator = get_phase_2_orchestrator()
    return orchestrator.process_query(query)


if __name__ == "__main__":
    # Demo the orchestrator with sample queries
    demo_queries = [
        "What is the expense ratio of the Small Cap Fund?",
        "Tell me about exit load for Liquid Fund",
        "Should I compare Small Cap vs Liquid?",  # Should trigger advisory
        "NAV of Ethical Fund",
    ]
    
    print("Phase 2 Orchestrator Demo")
    print("=" * 50)
    
    # Show system stats
    orchestrator = get_phase_2_orchestrator()
    stats = orchestrator.get_summary_stats()
    print(f"System Stats: {stats}")
    print()
    
    # Process demo queries
    for query in demo_queries:
        print(f"Query: {query}")
        print("-" * 30)
        
        try:
            result = run_phase_2(query)
            
            if result.advisory_triggered:
                print(f"ADVISORY: {result.advisory_reason}")
            elif result.has_results:
                top = result.top_result
                print(f"Found {len(result.filtered_candidates)} results")
                print(f"   Top: {top.chunk_type} (sim={top.similarity:.3f}, {top.retriever})")
                print(f"   Source: {top.source_url}")
            else:
                print("No relevant results found")
                
        except Exception as e:
            print(f"ERROR: {e}")
        
        print()
