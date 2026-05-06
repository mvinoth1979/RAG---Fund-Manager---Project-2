"""
Phase 0.5: Embed & Index
========================

Production-grade embedding and indexing pipeline using Google Gemini Cloud Embeddings.
Consumes semantic chunks from Phase 0.4 and produces:
- Vector index (Chroma DB persistent) with Google gemini-embedding-001
- Structured fact store (SQLite) for direct KV lookups
- Embedding artifacts for audit

Architecture reference: Section 4, Phase 0.5
Enforcement: Dimension 3072 (Gemini gemini-embedding-001); no NaN vectors; metadata binding mandatory
"""

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

DATA_CHUNKS = Path(os.getenv("DATA_CHUNKS", "./data/3_chunks"))
DATA_NORMALIZED = Path(os.getenv("DATA_NORMALIZED", "./data/2_normalized_text"))
DATA_EMBEDDINGS = Path(os.getenv("DATA_EMBEDDINGS", "./data/4_embeddings"))
DATA_STRUCTURED = Path(os.getenv("DATA_STRUCTURED", "./data/5_structured_facts"))
DATA_CHROMA = Path(os.getenv("DATA_CHROMA", "./data/6_chroma_index"))

# Cloud Model: Google Gemini gemini-embedding-001
EMBEDDING_MODEL = "models/gemini-embedding-001"
EXPECTED_DIM = 3072
BATCH_SIZE = 16

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("phase_0_5_embed")


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    source_url: str
    chunk_type: str
    text: str
    token_count: int
    overlap: bool


@dataclass
class EmbedResult:
    chunk_id: str
    doc_id: str
    source_url: str
    chunk_type: str
    text: str
    embedding: List[float]
    l2_norm: float


@dataclass
class EmbedManifestEntry:
    doc_id: str
    chunks_embedded: int
    facts_stored: int
    error: Optional[str] = None


# =============================================================================
# Embedding Engine (Gemini Cloud)
# =============================================================================

class GeminiEmbedder:
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        logger.info(f"Initialized Gemini Embedder: {model_name}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Gemini API."""
        if not texts:
            return []
        
        try:
            # Batch call to Gemini
            result = genai.embed_content(
                model=self.model_name,
                content=texts,
                task_type="retrieval_document"
            )
            embeddings = result.get('embedding', [])
            return embeddings
        except Exception as e:
            logger.error(f"Gemini Embedding Error: {e}")
            time.sleep(2)
            raise e

    @staticmethod
    def l2_normalize(embedding: List[float]) -> List[float]:
        """L2-normalize an embedding vector."""
        arr = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm == 0:
            return arr.tolist()
        return (arr / norm).tolist()


# =============================================================================
# Validation
# =============================================================================

class EmbeddingValidator:
    @staticmethod
    def validate(embedding: List[float], chunk_id: str) -> Optional[str]:
        """Return error string if invalid, else None."""
        if len(embedding) != EXPECTED_DIM:
            return f"Dimension mismatch: expected {EXPECTED_DIM}, got {len(embedding)}"

        arr = np.array(embedding, dtype=np.float32)
        if np.isnan(arr).any():
            return "NaN values detected"

        norm = np.linalg.norm(arr)
        if norm == 0:
            return "Zero vector detected"

        return None


# =============================================================================
# Storage Backends
# =============================================================================

class ChromaStore:
    def __init__(self, persist_dir: Path):
        import chromadb

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name="mutual_fund_chunks",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Chroma collection ready at {self.persist_dir}")

    def upsert(self, records: List[EmbedResult]) -> int:
        """Upsert embedding records into Chroma."""
        if not records:
            return 0

        ids = [r.chunk_id for r in records]
        embeddings = [r.embedding for r in records]
        documents = [r.text for r in records]
        metadatas = [
            {
                "doc_id": r.doc_id,
                "source_url": r.source_url,
                "chunk_type": r.chunk_type,
            }
            for r in records
        ]

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(records)

    def count(self) -> int:
        return self.collection.count()

    def clear(self):
        """Reset the collection for fresh indexing."""
        try:
            self.client.delete_collection("mutual_fund_chunks")
        except:
            pass
        self.collection = self.client.get_or_create_collection(
            name="mutual_fund_chunks",
            metadata={"hnsw:space": "cosine"},
        )


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS structured_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    fact_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    indexed_at TEXT NOT NULL
                )
                """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_facts_doc_type
                ON structured_facts(doc_id, fact_type)
                """)
            conn.commit()

    def clear_doc_facts(self, doc_id: str):
        """Remove existing facts for a doc_id to ensure idempotency."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM structured_facts WHERE doc_id = ?",
                (doc_id,),
            )
            conn.commit()

    def load_typed_facts(self, typed_facts_path: Path) -> int:
        """Load typed facts from normalized JSON into SQLite."""
        with open(typed_facts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        facts = data.get("typed_facts", [])
        doc_id = data.get("doc_id", "")
        source_url = data.get("source_url", "")
        indexed_at = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            for fact in facts:
                conn.execute(
                    """
                    INSERT INTO structured_facts
                    (doc_id, source_url, fact_type, value, confidence, indexed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        source_url,
                        fact.get("fact_type", ""),
                        fact.get("value", ""),
                        fact.get("confidence", ""),
                        indexed_at,
                    ),
                )
            conn.commit()

        return len(facts)


def save_embeddings(records: List[EmbedResult], output_dir: Path) -> Path:
    """Save embeddings as JSON for audit/reuse."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / "embeddings.json"
    payload = []
    for r in records:
        payload.append(
            {
                "chunk_id": r.chunk_id,
                "doc_id": r.doc_id,
                "source_url": r.source_url,
                "chunk_type": r.chunk_type,
                "text": r.text,
                "embedding": r.embedding,
                "l2_norm": r.l2_norm,
            }
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return path


# =============================================================================
# Main Entry Point
# =============================================================================

def run_embed_phase() -> Dict[str, Any]:
    """
    Execute Phase 0.5 using Gemini Cloud Embeddings.
    """
    logger.info("=" * 60)
    logger.info(f"PHASE 0.5: EMBED & INDEX ({EMBEDDING_MODEL})")
    logger.info("=" * 60)

    embedder = GeminiEmbedder()
    validator = EmbeddingValidator()
    chroma = ChromaStore(DATA_CHROMA)
    
    logger.info("Re-initializing vector store...")
    chroma.clear()
    
    sqlite = SQLiteStore(DATA_STRUCTURED / "facts.db")

    manifest = {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "model": EMBEDDING_MODEL,
        "expected_dim": EXPECTED_DIM,
        "total_chunks": 0,
        "embedded": 0,
        "rejected": 0,
        "facts_stored": 0,
        "results": [],
    }

    all_records: List[EmbedResult] = []

    chunk_files = sorted(DATA_CHUNKS.glob("DOC-*_chunks.jsonl"))
    if not chunk_files:
        logger.warning(f"No chunk files found in {DATA_CHUNKS}")
        return manifest

    # Process each document
    for chunk_file in chunk_files:
        doc_id = chunk_file.stem.replace("_chunks", "")
        logger.info(f"Embedding {doc_id} ...")

        entry = EmbedManifestEntry(doc_id=doc_id, chunks_embedded=0, facts_stored=0)

        chunks: List[ChunkRecord] = []
        with open(chunk_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    obj = json.loads(line)
                    chunks.append(
                        ChunkRecord(
                            chunk_id=obj["chunk_id"],
                            doc_id=obj["doc_id"],
                            source_url=obj["source_url"],
                            chunk_type=obj["chunk_type"],
                            text=obj["text"],
                            token_count=obj["token_count"],
                            overlap=obj.get("overlap", False),
                        )
                    )

        manifest["total_chunks"] += len(chunks)

        doc_records: List[EmbedResult] = []
        
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i+BATCH_SIZE]
            texts = [c.text for c in batch]
            raw_embeddings = embedder.embed(texts)

            for chunk, emb in zip(batch, raw_embeddings):
                normalized = embedder.l2_normalize(emb)
                error = validator.validate(normalized, chunk.chunk_id)
                if error:
                    logger.error(f"Validation failed for {chunk.chunk_id}: {error}")
                    manifest["rejected"] += 1
                    continue

                norm = float(np.linalg.norm(np.array(normalized, dtype=np.float32)))
                doc_records.append(
                    EmbedResult(
                        chunk_id=chunk.chunk_id,
                        doc_id=chunk.doc_id,
                        source_url=chunk.source_url,
                        chunk_type=chunk.chunk_type,
                        text=chunk.text,
                        embedding=normalized,
                        l2_norm=norm,
                    )
                )

        # Upsert to Chroma
        if doc_records:
            chroma.upsert(doc_records)
            all_records.extend(doc_records)

        entry.chunks_embedded = len(doc_records)
        manifest["embedded"] += len(doc_records)

        # Load facts
        facts_file = DATA_NORMALIZED / f"{doc_id}_typed_facts.json"
        if facts_file.exists():
            sqlite.clear_doc_facts(doc_id)
            fact_count = sqlite.load_typed_facts(facts_file)
            entry.facts_stored = fact_count
            manifest["facts_stored"] += fact_count

        manifest["results"].append(
            {
                "doc_id": entry.doc_id,
                "chunks_embedded": entry.chunks_embedded,
                "facts_stored": entry.facts_stored,
            }
        )

    # Save artifacts
    if all_records:
        save_embeddings(all_records, DATA_EMBEDDINGS)

    # Final count
    manifest["chroma_count"] = chroma.count()
    
    manifest_path = DATA_EMBEDDINGS / "embed_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info("-" * 60)
    logger.info(f"Embed complete. Total vectors: {manifest['chroma_count']}")
    logger.info("=" * 60)

    return manifest


if __name__ == "__main__":
    run_embed_phase()
