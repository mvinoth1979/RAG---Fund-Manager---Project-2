import json
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# Dynamically import the new Gemini Embedder from Phase 0
_EMBEDDER_PATH = PROJECT_ROOT / "phase_0_ingestion" / "0.5_embed_index" / "embedder.py"
_embedder_spec = importlib.util.spec_from_file_location("embedder", _EMBEDDER_PATH)
_embedder_mod = importlib.util.module_from_spec(_embedder_spec)
_embedder_spec.loader.exec_module(_embedder_mod)

GeminiEmbedder = _embedder_mod.GeminiEmbedder
EXPECTED_DIM = _embedder_mod.EXPECTED_DIM

logger = logging.getLogger("phase_2_3_hybrid")

class RetrievalCandidate(BaseModel):
    chunk_id: str
    doc_id: str
    source_url: str
    chunk_type: str
    text: str
    similarity: float
    rank: int
    retriever: str

class HybridRetriever:
    RRF_K = 60
    DENSE_TOPK = 10
    BM25_TOPK = 10

    DOC_ID_TO_NAME = {
        "DOC-001": "The Wealth Company Small Cap Fund",
        "DOC-002": "The Wealth Company Ethical Fund",
        "DOC-003": "The Wealth Company Multi Asset Allocation Fund",
        "DOC-004": "The Wealth Company Flexi Cap Fund",
        "DOC-005": "The Wealth Company Gold ETF FoF",
        "DOC-006": "The Wealth Company Liquid Fund",
        "DOC-007": "The Wealth Company Arbitrage Fund",
    }

    def __init__(
        self,
        chroma_dir: Path = PROJECT_ROOT / "data" / "6_chroma_index",
        chunks_dir: Path = PROJECT_ROOT / "data" / "3_chunks",
        sqlite_db: Path = PROJECT_ROOT / "data" / "5_structured_facts" / "facts.db",
    ):
        import chromadb
        from rank_bm25 import BM25Okapi

        self.chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
        self.collection = self.chroma_client.get_collection("mutual_fund_chunks")
        self.chunks = self._load_chunks(chunks_dir)
        self.chunk_index = {c["chunk_id"]: c for c in self.chunks}
        tokenized_corpus = [self._tokenize(c["text"]) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.sqlite_db = sqlite_db
        
        # Use Gemini Cloud Embedder (3072-dim)
        self.embedder = GeminiEmbedder()

        logger.info(f"Hybrid retriever ready (Gemini {EXPECTED_DIM}-dim). Chunks={len(self.chunks)} Chroma={self.collection.count()}")

    @staticmethod
    def _load_chunks(chunks_dir: Path) -> List[Dict]:
        chunks: List[Dict] = []
        for f in sorted(Path(chunks_dir).glob("DOC-*_chunks.jsonl")):
            with open(f, "r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        chunks.append(json.loads(line))
        return chunks

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        import re
        return re.findall(r"\b\w+\b", text.lower())

    def _dense_search(self, query: str, doc_ids: List[str]) -> List[Tuple[str, float]]:
        # API call to Gemini for query embedding
        embedding = self.embedder.embed([query])[0]
        embedding = GeminiEmbedder.l2_normalize(embedding)
        
        where_filter = {"doc_id": {"$in": doc_ids}} if doc_ids else None
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=self.DENSE_TOPK,
            where=where_filter,
            include=["metadatas", "distances"],
        )
        candidates: List[Tuple[str, float]] = []
        if results["ids"] and results["ids"][0]:
            for chunk_id, distance in zip(results["ids"][0], results["distances"][0]):
                similarity = 1.0 - float(distance)
                candidates.append((chunk_id, similarity))
        return candidates

    def _bm25_search(self, query: str, doc_ids: List[str] = None) -> Tuple[List[Tuple[str, float]], float]:
        tokens = self._tokenize(query)
        scores = self.bm25.get_scores(tokens)
        scored_indices = list(enumerate(scores))
        if doc_ids:
            scored_indices = [(idx, score) for idx, score in scored_indices if self.chunks[idx]["doc_id"] in doc_ids]
        ranked = sorted(scored_indices, key=lambda x: x[1], reverse=True)[:self.BM25_TOPK]
        max_score = ranked[0][1] if ranked else 1.0
        candidates = [(self.chunks[idx]["chunk_id"], float(score)) for idx, score in ranked]
        return candidates, max_score

    def _structured_lookup(self, doc_ids: List[str], fact_type: Optional[str], fact_confidence: float) -> Optional[Dict]:
        if fact_confidence < 0.8 or len(doc_ids) != 1 or not fact_type:
            return None
        doc_id = doc_ids[0]
        fund_name = self.DOC_ID_TO_NAME.get(doc_id, doc_id)
        
        with sqlite3.connect(self.sqlite_db) as conn:
            row = conn.execute("SELECT value FROM structured_facts WHERE doc_id = ? AND fact_type = ?", (doc_id, fact_type)).fetchone()
        if not row:
            return None
        
        source_url = ""
        for chunk in self.chunks:
            if chunk["doc_id"] == doc_id:
                source_url = chunk["source_url"]
                if chunk["chunk_type"] == fact_type:
                    return {
                        "chunk_id": chunk["chunk_id"],
                        "doc_id": doc_id,
                        "source_url": chunk["source_url"],
                        "chunk_type": fact_type,
                        "text": f"The {fact_type.replace('_', ' ')} for {fund_name} is {row[0]}.",
                        "similarity": 1.0,
                        "retriever": "structured",
                    }
        return {
            "chunk_id": f"structured_{doc_id}_{fact_type}",
            "doc_id": doc_id,
            "source_url": source_url,
            "chunk_type": fact_type,
            "text": f"The {fact_type.replace('_', ' ')} for {fund_name} is {row[0]}.",
            "similarity": 1.0,
            "retriever": "structured",
        }

    def _rrf_fusion(self, dense: List[Tuple[str, float]], bm25: List[Tuple[str, float]], structured: Optional[Dict]) -> List[RetrievalCandidate]:
        dense_ranks = {cid: rank + 1 for rank, (cid, _) in enumerate(dense)}
        bm25_ranks = {cid: rank + 1 for rank, (cid, _) in enumerate(bm25)}
        dense_sims = {cid: sim for cid, sim in dense}
        bm25_scores = {cid: score for cid, score in bm25}
        max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
        all_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys())
        structured_id = structured["chunk_id"] if structured else None
        if structured_id: all_ids.add(structured_id)
        rrf_scores = {}
        for cid in all_ids:
            score = 0.0
            if cid in dense_ranks: score += 1.0 / (self.RRF_K + dense_ranks[cid])
            if cid in bm25_ranks: score += 1.0 / (self.RRF_K + bm25_ranks[cid])
            if cid == structured_id: score += 1.0 / (self.RRF_K + 1)
            rrf_scores[cid] = score
        ranked_ids = sorted(rrf_scores.keys(), key=lambda c: -rrf_scores[c])
        candidates = []
        for rank, cid in enumerate(ranked_ids, start=1):
            if cid == structured_id and structured:
                sim, label, chunk_data = 1.0, "structured", structured
            elif cid in dense_sims:
                sim, label, chunk_data = dense_sims[cid], ("dense+bm25" if cid in bm25_scores else "dense"), self.chunk_index.get(cid)
            elif cid in bm25_scores:
                normalized = (0.75 + (bm25_scores[cid] / max_bm25) * 0.15) if max_bm25 > 0 else 0.75
                sim, label, chunk_data = min(normalized, 0.90), "bm25", self.chunk_index.get(cid)
            else: continue
            if not chunk_data: continue
            candidates.append(RetrievalCandidate(chunk_id=chunk_data["chunk_id"], doc_id=chunk_data["doc_id"], source_url=chunk_data["source_url"], chunk_type=chunk_data["chunk_type"], text=chunk_data["text"], similarity=round(sim, 4), rank=rank, retriever=label))
        return candidates

    def retrieve(self, normalized_query: str, mentioned_funds: List[str], fact_type: Optional[str], fact_confidence: float) -> List[RetrievalCandidate]:
        logger.info(f"Retrieving for: {normalized_query[:80]}...")
        dense_results = self._dense_search(normalized_query, mentioned_funds)
        bm25_results, _ = self._bm25_search(normalized_query, mentioned_funds)
        structured_result = self._structured_lookup(mentioned_funds, fact_type, fact_confidence)
        fused = self._rrf_fusion(dense_results, bm25_results, structured_result)
        return fused

def run_hybrid_retrieval(normalized_query: str, mentioned_funds: List[str], fact_type: Optional[str], fact_confidence: float) -> List[RetrievalCandidate]:
    retriever = HybridRetriever()
    return retriever.retrieve(normalized_query=normalized_query, mentioned_funds=mentioned_funds, fact_type=fact_type, fact_confidence=fact_confidence)
