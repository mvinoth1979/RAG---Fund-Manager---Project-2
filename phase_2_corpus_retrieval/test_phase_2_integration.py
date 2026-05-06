"""
Phase 2 Integration Test
========================
Tests the complete Phase 2: Corpus Retrieval pipeline:
2.1 Query Normalization -> 2.2 Entity Resolution -> 2.3 Hybrid Retrieval -> 2.4 Relevance Filtering
"""

import logging
import sys
from pathlib import Path
from typing import List

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
logger = logging.getLogger("phase_2_integration_test")


class Phase2IntegrationTest:
    """
    Complete Phase 2 pipeline test with real data and edge cases.
    """

    def __init__(self):
        self.normalizer = QueryNormalizer()
        self.entity_resolver = EntityResolver()
        self.hybrid_retriever = HybridRetriever()
        self.relevance_filter = RelevanceFilter()

    def run_complete_pipeline(self, query: str) -> dict:
        """
        Execute the complete Phase 2 pipeline and return all intermediate results.
        """
        logger.info(f"Testing query: '{query}'")
        
        # Step 2.1: Query Normalization
        normalized = self.normalizer.normalize(query)
        logger.info(f"2.1 Normalized: '{normalized.normalized}'")
        logger.info(f"    Transformations: {normalized.transformations}")
        
        # Step 2.2: Entity Resolution
        resolved = self.entity_resolver.resolve(normalized.original, normalized.normalized)
        logger.info(f"2.2 Resolved funds: {resolved.mentioned_funds}")
        logger.info(f"    Fact type: {resolved.fact_type} (confidence: {resolved.fact_confidence})")
        logger.info(f"    Advisory trigger: {resolved.advisory_trigger}")
        
        if resolved.advisory_trigger:
            logger.warning(f"ADVISORY TRIGGERED: {resolved.advisory_reason}")
            return {
                "query": query,
                "normalized": normalized,
                "resolved": resolved,
                "candidates": [],
                "filtered": [],
                "advisory_triggered": True,
                "advisory_reason": resolved.advisory_reason
            }
        
        # Step 2.3: Hybrid Retrieval
        candidates = self.hybrid_retriever.retrieve(
            normalized_query=resolved.normalized_query,
            mentioned_funds=resolved.mentioned_funds,
            fact_type=resolved.fact_type,
            fact_confidence=resolved.fact_confidence
        )
        logger.info(f"2.3 Retrieved {len(candidates)} candidates")
        
        # Step 2.4: Relevance Filtering
        filtered = self.relevance_filter.filter(candidates)
        logger.info(f"2.4 Filtered to {len(filtered)} candidates (threshold: {self.relevance_filter.THRESHOLD})")
        
        return {
            "query": query,
            "normalized": normalized,
            "resolved": resolved,
            "candidates": candidates,
            "filtered": filtered,
            "advisory_triggered": False,
            "advisory_reason": ""
        }

    def test_factual_queries(self):
        """Test various factual query patterns."""
        test_queries = [
            "What is the expense ratio of the Small Cap Fund?",
            "Tell me the exit load for the Liquid Fund",
            "What is the minimum SIP amount for Flexi Cap Fund?",
            "NAV of Ethical Fund",
            "Benchmark for Multi Asset Allocation Fund",
            "Risk level of Gold ETF FOF",
            "Fund manager for Arbitrage Fund",
            "Inception date of Small Cap Fund",
        ]
        
        logger.info("=" * 60)
        logger.info("TESTING FACTUAL QUERIES")
        logger.info("=" * 60)
        
        results = []
        for query in test_queries:
            try:
                result = self.run_complete_pipeline(query)
                results.append(result)
                
                # Print summary
                status = "ADVISORY" if result["advisory_triggered"] else f"OK ({len(result['filtered'])} results)"
                logger.info(f"✓ {query[:40]:<40} -> {status}")
                
                # Show top filtered result if available
                if result["filtered"]:
                    top = result["filtered"][0]
                    logger.info(f"    Top: {top.chunk_type} (sim={top.similarity:.3f}, {top.retriever})")
                
            except Exception as e:
                logger.error(f"✗ FAILED: {query} - {str(e)}")
                results.append({"query": query, "error": str(e)})
        
        return results

    def test_advisory_queries(self):
        """Test queries that should trigger advisory refusal."""
        advisory_queries = [
            "Should I invest in Small Cap Fund?",
            "Which fund is better - Flexi Cap or Liquid?",
            "Compare Small Cap vs Ethical Fund",
            "Is it safe to invest in Gold ETF?",
            "What fund should I buy for retirement?",
            "Will Multi Asset Allocation outperform?",
            "Recommend me a good mutual fund",
        ]
        
        logger.info("=" * 60)
        logger.info("TESTING ADVISORY QUERIES (should trigger refusal)")
        logger.info("=" * 60)
        
        results = []
        for query in advisory_queries:
            try:
                result = self.run_complete_pipeline(query)
                results.append(result)
                
                if result["advisory_triggered"]:
                    logger.info(f"✓ ADVISORY TRIGGERED: {query[:40]:<40}")
                    logger.info(f"    Reason: {result['advisory_reason']}")
                else:
                    logger.warning(f"⚠ ADVISORY NOT TRIGGERED: {query[:40]:<40}")
                    
            except Exception as e:
                logger.error(f"✗ FAILED: {query} - {str(e)}")
                results.append({"query": query, "error": str(e)})
        
        return results

    def test_edge_cases(self):
        """Test edge cases and ambiguous queries."""
        edge_queries = [
            "What about returns?",  # No specific fund mentioned
            "Tell me everything",   # Vague query
            "Small Cap expense ratio and exit load",  # Multiple facts
            "",  # Empty query
            "xyz abc 123",  # Gibberish
        ]
        
        logger.info("=" * 60)
        logger.info("TESTING EDGE CASES")
        logger.info("=" * 60)
        
        results = []
        for query in edge_queries:
            try:
                result = self.run_complete_pipeline(query)
                results.append(result)
                
                status = "ADVISORY" if result["advisory_triggered"] else f"OK ({len(result['filtered'])} results)"
                logger.info(f"✓ '{query[:30]:<30}' -> {status}")
                
            except Exception as e:
                logger.error(f"✗ FAILED: '{query}' - {str(e)}")
                results.append({"query": query, "error": str(e)})
        
        return results

    def run_all_tests(self):
        """Run all test suites and return summary."""
        logger.info("Starting Phase 2 Integration Tests")
        logger.info("=" * 60)
        
        factual_results = self.test_factual_queries()
        advisory_results = self.test_advisory_queries()
        edge_results = self.test_edge_cases()
        
        # Summary
        logger.info("=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        
        total_queries = len(factual_results) + len(advisory_results) + len(edge_results)
        successful = sum(1 for r in factual_results + advisory_results + edge_results if "error" not in r)
        advisory_triggered = sum(1 for r in advisory_results if r.get("advisory_triggered", False))
        factual_with_results = sum(1 for r in factual_results if not r.get("advisory_triggered", False) and len(r.get("filtered", [])) > 0)
        
        logger.info(f"Total queries tested: {total_queries}")
        logger.info(f"Successful executions: {successful}/{total_queries}")
        logger.info(f"Advisory correctly triggered: {advisory_triggered}/{len(advisory_results)}")
        logger.info(f"Factual queries with results: {factual_with_results}/{len(factual_results)}")
        
        return {
            "total_queries": total_queries,
            "successful": successful,
            "advisory_triggered": advisory_triggered,
            "factual_with_results": factual_with_results,
            "factual_results": factual_results,
            "advisory_results": advisory_results,
            "edge_results": edge_results
        }


def main():
    """Run the integration tests."""
    tester = Phase2IntegrationTest()
    results = tester.run_all_tests()
    
    # Print final status
    if results["successful"] == results["total_queries"]:
        logger.info("🎉 All tests completed successfully!")
    else:
        logger.warning(f"⚠ {results['total_queries'] - results['successful']} tests failed")
    
    return results


if __name__ == "__main__":
    main()
