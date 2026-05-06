"""
Phase 0.5 Verification Script
Checks all outputs against architecture.md requirements.
"""
import json
import sqlite3
import numpy as np
from pathlib import Path

# Paths
EMBEDDINGS_FILE = Path("./data/4_embeddings/embeddings.json")
MANIFEST_FILE = Path("./data/4_embeddings/embed_manifest.json")
CHROMA_DIR = Path("./data/6_chroma_index")
DB_PATH = Path("./data/5_structured_facts/facts.db")

EXPECTED_DIM = 1024
EXPECTED_CHUNKS = 28
EXPECTED_DOCS = 7

def check_manifest():
    print("=" * 60)
    print("1. EMBED MANIFEST CHECK")
    print("=" * 60)
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    checks = [
        ("model", manifest.get("model"), "BAAI/bge-large-en-v1.5"),
        ("expected_dim", manifest.get("expected_dim"), EXPECTED_DIM),
        ("total_chunks", manifest.get("total_chunks"), EXPECTED_CHUNKS),
        ("embedded", manifest.get("embedded"), EXPECTED_CHUNKS),
        ("rejected", manifest.get("rejected"), 0),
        ("chroma_count", manifest.get("chroma_count"), EXPECTED_CHUNKS),
        ("result_count", len(manifest.get("results", [])), EXPECTED_DOCS),
    ]

    for name, actual, expected in checks:
        status = "PASS" if actual == expected else "FAIL"
        print(f"  [{status}] {name}: {actual} (expected: {expected})")

    doc_results = manifest.get("results", [])
    chunk_sum = sum(r["chunks_embedded"] for r in doc_results)
    fact_sum = sum(r["facts_stored"] for r in doc_results)
    print(f"  [{'PASS' if chunk_sum == EXPECTED_CHUNKS else 'FAIL'}] chunk_sum: {chunk_sum}")
    print(f"  [INFO] facts_stored total: {fact_sum}")

    # Check all docs have no errors
    errors = [r for r in doc_results if r.get("error")]
    print(f"  [{'PASS' if not errors else 'FAIL'}] No errors in any doc ({len(errors)} errors)")
    return manifest

def check_embeddings():
    print("\n" + "=" * 60)
    print("2. EMBEDDINGS.JSON VALIDATION")
    print("=" * 60)
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"  [INFO] Total records: {len(records)}")

    dims_ok = 0
    nan_ok = 0
    inf_ok = 0
    norm_ok = 0
    meta_ok = 0

    for r in records:
        emb = r["embedding"]
        arr = np.array(emb, dtype=np.float32)

        if len(emb) == EXPECTED_DIM:
            dims_ok += 1
        if not np.isnan(arr).any():
            nan_ok += 1
        if not np.isinf(arr).any():
            inf_ok += 1
        norm = np.linalg.norm(arr)
        if abs(norm - 1.0) <= 0.01:
            norm_ok += 1
        if r.get("doc_id") and r.get("source_url") and r.get("chunk_type"):
            meta_ok += 1

    total = len(records)
    print(f"  [{'PASS' if dims_ok == total else 'FAIL'}] Dimension == 1024: {dims_ok}/{total}")
    print(f"  [{'PASS' if nan_ok == total else 'FAIL'}] No NaN: {nan_ok}/{total}")
    print(f"  [{'PASS' if inf_ok == total else 'FAIL'}] No Inf: {inf_ok}/{total}")
    print(f"  [{'PASS' if norm_ok == total else 'FAIL'}] L2 norm ~1.0: {norm_ok}/{total}")
    print(f"  [{'PASS' if meta_ok == total else 'FAIL'}] Metadata binding: {meta_ok}/{total}")

    # Check doc_id distribution
    doc_counts = {}
    for r in records:
        doc_counts[r["doc_id"]] = doc_counts.get(r["doc_id"], 0) + 1
    print(f"  [INFO] Chunks per doc: {doc_counts}")
    return records

def check_chroma():
    print("\n" + "=" * 60)
    print("3. CHROMA DB CHECK")
    print("=" * 60)
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection("mutual_fund_chunks")

    count = collection.count()
    print(f"  [{'PASS' if count == EXPECTED_CHUNKS else 'FAIL'}] Collection count: {count} (expected {EXPECTED_CHUNKS})")

    # Peek at metadata schema
    result = collection.get(limit=1)
    if result and result.get("metadatas"):
        meta = result["metadatas"][0]
        required_keys = {"doc_id", "source_url", "chunk_type"}
        has_keys = required_keys.issubset(set(meta.keys()))
        print(f"  [{'PASS' if has_keys else 'FAIL'}] Metadata keys: {list(meta.keys())}")

    # Verify collection metadata (hnsw:space)
    print(f"  [INFO] Collection metadata: {collection.metadata}")
    return count

def check_sqlite():
    print("\n" + "=" * 60)
    print("4. SQLITE STRUCTURED FACTS CHECK")
    print("=" * 60)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table schema check
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='structured_facts'")
    table_exists = cursor.fetchone() is not None
    print(f"  [{'PASS' if table_exists else 'FAIL'}] Table 'structured_facts' exists")

    # Index check
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_facts_doc_type'")
    index_exists = cursor.fetchone() is not None
    print(f"  [{'PASS' if index_exists else 'FAIL'}] Index 'idx_facts_doc_type' exists")

    # Count total facts
    cursor.execute("SELECT COUNT(*) FROM structured_facts")
    total_facts = cursor.fetchone()[0]
    print(f"  [INFO] Total facts: {total_facts}")

    # Count per doc
    cursor.execute("SELECT doc_id, COUNT(*) FROM structured_facts GROUP BY doc_id ORDER BY doc_id")
    per_doc = cursor.fetchall()
    print(f"  [INFO] Facts per doc: {dict(per_doc)}")

    # Verify all 7 docs present
    doc_ids = [r[0] for r in per_doc]
    expected_docs = [f"DOC-{i:03d}" for i in range(1, 8)]
    all_present = set(expected_docs).issubset(set(doc_ids))
    print(f"  [{'PASS' if all_present else 'FAIL'}] All 7 docs have facts: {all_present}")

    # Sample a fact
    cursor.execute("SELECT doc_id, fact_type, value, confidence FROM structured_facts LIMIT 1")
    sample = cursor.fetchone()
    if sample:
        print(f"  [INFO] Sample fact: doc_id={sample[0]}, type={sample[1]}, value={sample[2][:60]}..., confidence={sample[3]}")

    # Check columns
    cursor.execute("PRAGMA table_info(structured_facts)")
    columns = [c[1] for c in cursor.fetchall()]
    expected_cols = ["id", "doc_id", "source_url", "fact_type", "value", "confidence", "indexed_at"]
    cols_ok = all(c in columns for c in expected_cols)
    print(f"  [{'PASS' if cols_ok else 'FAIL'}] All required columns present: {columns}")

    conn.close()
    return total_facts

def main():
    print("PHASE 0.5 VERIFICATION REPORT")
    print("=" * 60)

    manifest = check_manifest()
    records = check_embeddings()
    chroma_count = check_chroma()
    sqlite_count = check_sqlite()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Manifest:      {manifest['embedded']} chunks, {manifest['facts_stored']} facts, {manifest['rejected']} rejected")
    print(f"  Embeddings:    {len(records)} records validated (dim={EXPECTED_DIM}, L2-norm, no NaN)")
    print(f"  Chroma DB:     {chroma_count} vectors with metadata binding")
    print(f"  SQLite:        {sqlite_count} structured facts across 7 docs")
    print("=" * 60)

if __name__ == "__main__":
    main()
