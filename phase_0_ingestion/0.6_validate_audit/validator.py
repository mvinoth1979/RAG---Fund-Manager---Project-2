"""
Phase 0.6: Validate & Audit
============================
Production-grade validation and atomic active/shadow index swap.
Consumes Phase 0.5 outputs and produces an active index registry + audit logs.

Architecture reference: Section 4, Phase 0.6
Enforcement: All 7 docs must produce >=1 chunk; old index retained 7 days for rollback.
"""

import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# =============================================================================
# Configuration
# =============================================================================

DATA_CHUNKS = Path(os.getenv("DATA_CHUNKS", "./data/3_chunks"))
DATA_EMBEDDINGS = Path(os.getenv("DATA_EMBEDDINGS", "./data/4_embeddings"))
DATA_STRUCTURED = Path(os.getenv("DATA_STRUCTURED", "./data/5_structured_facts"))
DATA_CHROMA = Path(os.getenv("DATA_CHROMA", "./data/6_chroma_index"))
DATA_AUDIT = Path(os.getenv("DATA_AUDIT", "./data/7_audit_logs"))
DATA_BACKUP = Path(os.getenv("DATA_BACKUP", "./data/rollback_backups"))
REGISTRY_FILE = Path(os.getenv("INDEX_REGISTRY", "./data/index_registry.json"))

EXPECTED_DIM = 1024
EXPECTED_DOCS = 7
EXPECTED_MODEL = "BAAI/bge-large-en-v1.5"
BACKUP_RETENTION_DAYS = 7

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("phase_0_6_validate")


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    run_id: str
    timestamp: str
    passed: bool
    checks: List[CheckResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    embeddings_hash: str = ""
    summary: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Schema Validator
# =============================================================================


class SchemaValidator:
    def validate_manifest(self, manifest: Dict) -> CheckResult:
        """Validate embed_manifest.json schema and values."""
        required_keys = {
            "run_id",
            "model",
            "expected_dim",
            "total_chunks",
            "embedded",
            "rejected",
            "chroma_count",
            "results",
        }
        missing = required_keys - set(manifest.keys())
        if missing:
            return CheckResult(
                name="manifest_schema",
                passed=False,
                message=f"Missing manifest keys: {missing}",
            )

        checks = []
        if manifest["model"] != EXPECTED_MODEL:
            checks.append(f"model mismatch: {manifest['model']}")
        if manifest["expected_dim"] != EXPECTED_DIM:
            checks.append(f"dim mismatch: {manifest['expected_dim']}")
        if manifest.get("rejected", 0) != 0:
            checks.append(f"rejected > 0: {manifest['rejected']}")
        if len(manifest.get("results", [])) != EXPECTED_DOCS:
            checks.append(
                f"doc count mismatch: {len(manifest.get('results', []))}"
            )

        if checks:
            return CheckResult(
                name="manifest_schema",
                passed=False,
                message="; ".join(checks),
                details={"issues": checks},
            )

        return CheckResult(
            name="manifest_schema",
            passed=True,
            message="Manifest schema valid",
            details={
                "run_id": manifest["run_id"],
                "model": manifest["model"],
                "total_chunks": manifest["total_chunks"],
            },
        )

    def validate_embeddings_file(self, embeddings: List[Dict]) -> CheckResult:
        """Validate embeddings.json structure."""
        if not embeddings:
            return CheckResult(
                name="embeddings_structure",
                passed=False,
                message="Embeddings file is empty",
            )

        required_record_keys = {
            "chunk_id",
            "doc_id",
            "source_url",
            "chunk_type",
            "text",
            "embedding",
            "l2_norm",
        }
        issues = []
        for idx, rec in enumerate(embeddings):
            missing = required_record_keys - set(rec.keys())
            if missing:
                issues.append(f"Record {idx} missing keys: {missing}")
                break

        if issues:
            return CheckResult(
                name="embeddings_structure",
                passed=False,
                message="; ".join(issues),
                details={"issues": issues},
            )

        return CheckResult(
            name="embeddings_structure",
            passed=True,
            message=f"{len(embeddings)} records have required keys",
            details={"record_count": len(embeddings)},
        )

    def validate_chroma(self, chroma_count: int, manifest: Dict) -> CheckResult:
        """Validate Chroma DB state."""
        expected = manifest.get("chroma_count", 0)
        if chroma_count != expected:
            return CheckResult(
                name="chroma_validation",
                passed=False,
                message=f"Chroma count {chroma_count} != manifest {expected}",
                details={"chroma_count": chroma_count, "manifest_count": expected},
            )

        return CheckResult(
            name="chroma_validation",
            passed=True,
            message=f"Chroma count {chroma_count} matches manifest",
            details={"chroma_count": chroma_count},
        )

    def validate_sqlite(self, db_path: Path, manifest: Dict) -> CheckResult:
        """Validate SQLite structured facts schema and counts."""
        if not db_path.exists():
            return CheckResult(
                name="sqlite_validation",
                passed=False,
                message=f"SQLite DB not found: {db_path}",
            )

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='structured_facts'"
            )
            if not cursor.fetchone():
                return CheckResult(
                    name="sqlite_validation",
                    passed=False,
                    message="Table 'structured_facts' missing",
                )

            # Index exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_facts_doc_type'"
            )
            if not cursor.fetchone():
                return CheckResult(
                    name="sqlite_validation",
                    passed=False,
                    message="Index 'idx_facts_doc_type' missing",
                )

            # Column check
            cursor.execute("PRAGMA table_info(structured_facts)")
            columns = {c[1] for c in cursor.fetchall()}
            required = {"id", "doc_id", "source_url", "fact_type", "value", "confidence", "indexed_at"}
            if not required.issubset(columns):
                return CheckResult(
                    name="sqlite_validation",
                    passed=False,
                    message=f"Missing columns: {required - columns}",
                )

            # Count
            cursor.execute("SELECT COUNT(*) FROM structured_facts")
            count = cursor.fetchone()[0]
            expected_facts = manifest.get("facts_stored", 0)

        return CheckResult(
            name="sqlite_validation",
            passed=True,
            message=f"SQLite valid: {count} facts",
            details={"fact_count": count, "expected_facts": expected_facts},
        )


# =============================================================================
# Coverage Checker
# =============================================================================


class CoverageChecker:
    def check(
        self,
        manifest: Dict,
        embeddings: List[Dict],
        db_path: Path,
    ) -> CheckResult:
        """Ensure all 7 docs have >=1 chunk and >=1 fact."""
        issues = []

        # Manifest coverage
        results = manifest.get("results", [])
        doc_ids_manifest = {r["doc_id"] for r in results}
        if len(doc_ids_manifest) != EXPECTED_DOCS:
            issues.append(
                f"Expected {EXPECTED_DOCS} docs in manifest, got {len(doc_ids_manifest)}"
            )

        for r in results:
            if r["chunks_embedded"] < 1:
                issues.append(f"{r['doc_id']} has 0 chunks")
            if r["facts_stored"] < 1:
                issues.append(f"{r['doc_id']} has 0 facts")

        # Embedding coverage
        doc_ids_emb = {e["doc_id"] for e in embeddings}
        missing_emb = doc_ids_manifest - doc_ids_emb
        if missing_emb:
            issues.append(f"Docs missing from embeddings: {missing_emb}")

        # SQLite coverage
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT doc_id FROM structured_facts")
            doc_ids_db = {r[0] for r in cursor.fetchall()}

        missing_db = doc_ids_manifest - doc_ids_db
        if missing_db:
            issues.append(f"Docs missing from SQLite: {missing_db}")

        if issues:
            return CheckResult(
                name="coverage_check",
                passed=False,
                message="; ".join(issues),
                details={"issues": issues},
            )

        return CheckResult(
            name="coverage_check",
            passed=True,
            message=f"All {EXPECTED_DOCS} docs have chunks and facts",
            details={
                "docs_in_manifest": len(doc_ids_manifest),
                "docs_in_embeddings": len(doc_ids_emb),
                "docs_in_sqlite": len(doc_ids_db),
            },
        )


# =============================================================================
# Integrity Checker
# =============================================================================


class IntegrityChecker:
    @staticmethod
    def compute_file_hash(path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def verify_embeddings(
        self, embeddings: List[Dict]
    ) -> Tuple[CheckResult, str]:
        """Verify embedding dimensions, NaN, Inf, L2 norm. Compute hash."""
        issues = []
        dim_ok = 0
        nan_ok = 0
        inf_ok = 0
        norm_ok = 0

        for idx, rec in enumerate(embeddings):
            emb = rec["embedding"]
            if len(emb) != EXPECTED_DIM:
                issues.append(f"Record {idx} dim={len(emb)}")
                break
            dim_ok += 1

            arr = np.array(emb, dtype=np.float32)
            if np.isnan(arr).any():
                issues.append(f"Record {idx} has NaN")
                break
            nan_ok += 1

            if np.isinf(arr).any():
                issues.append(f"Record {idx} has Inf")
                break
            inf_ok += 1

            norm = np.linalg.norm(arr)
            if abs(norm - 1.0) > 0.01:
                issues.append(f"Record {idx} norm={norm:.4f}")
                break
            norm_ok += 1

        total = len(embeddings)
        hash_str = self.compute_file_hash(DATA_EMBEDDINGS / "embeddings.json")

        if issues:
            return (
                CheckResult(
                    name="embedding_integrity",
                    passed=False,
                    message="; ".join(issues),
                    details={
                        "dim_ok": dim_ok,
                        "nan_ok": nan_ok,
                        "inf_ok": inf_ok,
                        "norm_ok": norm_ok,
                        "total": total,
                    },
                ),
                hash_str,
            )

        return (
            CheckResult(
                name="embedding_integrity",
                passed=True,
                message=f"All {total} embeddings valid (dim={EXPECTED_DIM}, L2-norm, no NaN/Inf)",
                details={
                    "dim_ok": dim_ok,
                    "nan_ok": nan_ok,
                    "inf_ok": inf_ok,
                    "norm_ok": norm_ok,
                    "total": total,
                    "sha256": hash_str,
                },
            ),
            hash_str,
        )


# =============================================================================
# Index Swapper
# =============================================================================


class IndexSwapper:
    def __init__(self):
        self.registry_path = REGISTRY_FILE
        self.backup_dir = DATA_BACKUP
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def load_registry(self) -> Dict[str, Any]:
        if self.registry_path.exists():
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "active_run_id": None,
            "previous_run_id": None,
            "runs": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def save_registry(self, registry: Dict) -> bool:
        """Atomic write of registry file."""
        try:
            temp_path = self.registry_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            os.replace(str(temp_path), str(self.registry_path))
            return True
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
            return False

    def _sanitize_backup_name(self, run_id: str) -> str:
        """Sanitize run_id for use as a directory name on Windows."""
        return run_id.replace(":", "-").replace("+", "_")

    def backup_active_index(self, run_id: str) -> Optional[Path]:
        """Backup current active index artifacts for rollback."""
        if not run_id:
            return None

        backup_path = self.backup_dir / self._sanitize_backup_name(run_id)
        backup_path.mkdir(parents=True, exist_ok=True)

        # Backup embeddings
        src_emb = DATA_EMBEDDINGS
        dst_emb = backup_path / "embeddings"
        if src_emb.exists():
            shutil.copytree(src_emb, dst_emb, dirs_exist_ok=True)

        # Backup structured facts
        src_sqlite = DATA_STRUCTURED / "facts.db"
        dst_sqlite = backup_path / "facts.db"
        if src_sqlite.exists():
            shutil.copy2(src_sqlite, dst_sqlite)

        # Backup Chroma index
        src_chroma = DATA_CHROMA
        dst_chroma = backup_path / "chroma_index"
        if src_chroma.exists():
            shutil.copytree(src_chroma, dst_chroma, dirs_exist_ok=True)

        logger.info(f"Backed up active index to {backup_path}")
        return backup_path

    def swap(self, new_run_id: str, embeddings_hash: str) -> Tuple[bool, str]:
        """
        Atomically swap shadow (current data dirs) to active.
        Returns (success, message).
        """
        registry = self.load_registry()
        old_run_id = registry.get("active_run_id")

        # Backup old active before swap
        if old_run_id:
            self.backup_active_index(old_run_id)

        # Update registry
        registry["previous_run_id"] = old_run_id
        registry["active_run_id"] = new_run_id
        registry["last_swapped_at"] = datetime.now(timezone.utc).isoformat()

        run_entry = {
            "run_id": new_run_id,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "embeddings_hash": embeddings_hash,
            "paths": {
                "embeddings": str(DATA_EMBEDDINGS),
                "structured_facts": str(DATA_STRUCTURED / "facts.db"),
                "chroma_index": str(DATA_CHROMA),
            },
        }

        # Update or append run entry
        runs = registry.get("runs", [])
        existing = [r for r in runs if r["run_id"] == new_run_id]
        if existing:
            existing[0].update(run_entry)
        else:
            runs.append(run_entry)
        registry["runs"] = runs

        if not self.save_registry(registry):
            return False, "Registry atomic write failed"

        logger.info(f"Index swapped: {old_run_id} -> {new_run_id}")
        return True, f"Swapped {old_run_id} -> {new_run_id}"

    def cleanup_old_backups(self, retention_days: int = BACKUP_RETENTION_DAYS):
        """Remove backup directories older than retention_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        removed = 0

        if not self.backup_dir.exists():
            return

        for item in self.backup_dir.iterdir():
            if not item.is_dir():
                continue
            try:
                # Try to parse directory name as ISO timestamp
                mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    shutil.rmtree(item)
                    removed += 1
                    logger.info(f"Removed old backup: {item}")
            except Exception as e:
                logger.warning(f"Could not process backup {item}: {e}")

        logger.info(f"Cleanup complete: removed {removed} old backups")


# =============================================================================
# Audit Logger
# =============================================================================


class AuditLogger:
    def __init__(self, audit_dir: Path = DATA_AUDIT):
        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def log(self, report: ValidationReport):
        filename = f"validation_{report.run_id.replace(':', '-').replace('+', '_')}.json"
        path = self.audit_dir / filename

        payload = {
            "run_id": report.run_id,
            "timestamp": report.timestamp,
            "passed": report.passed,
            "embeddings_hash": report.embeddings_hash,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "details": c.details,
                }
                for c in report.checks
            ],
            "errors": report.errors,
            "summary": report.summary,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        logger.info(f"Audit log written to {path}")
        return path


# =============================================================================
# Main Entry Point
# =============================================================================


def run_validate_phase() -> ValidationReport:
    """
    Execute Phase 0.6 Validate & Audit.
    """
    logger.info("=" * 60)
    logger.info("PHASE 0.6: VALIDATE & AUDIT")
    logger.info("=" * 60)

    schema_validator = SchemaValidator()
    coverage_checker = CoverageChecker()
    integrity_checker = IntegrityChecker()
    swapper = IndexSwapper()
    auditor = AuditLogger()

    report = ValidationReport(
        run_id="",
        timestamp=datetime.now(timezone.utc).isoformat(),
        passed=False,
    )

    # ------------------------------------------------------------------
    # 1. Load manifest
    # ------------------------------------------------------------------
    manifest_path = DATA_EMBEDDINGS / "embed_manifest.json"
    if not manifest_path.exists():
        report.errors.append(f"Manifest not found: {manifest_path}")
        auditor.log(report)
        logger.error("Validation aborted: manifest missing")
        return report

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    report.run_id = manifest.get("run_id", "unknown")
    logger.info(f"Validating run_id: {report.run_id}")

    # ------------------------------------------------------------------
    # 2. Schema validation
    # ------------------------------------------------------------------
    manifest_check = schema_validator.validate_manifest(manifest)
    report.checks.append(manifest_check)
    if not manifest_check.passed:
        report.errors.append(manifest_check.message)

    # Load embeddings
    embeddings_path = DATA_EMBEDDINGS / "embeddings.json"
    embeddings = []
    if embeddings_path.exists():
        with open(embeddings_path, "r", encoding="utf-8") as f:
            embeddings = json.load(f)
    else:
        report.errors.append(f"Embeddings file not found: {embeddings_path}")

    if embeddings:
        emb_struct_check = schema_validator.validate_embeddings_file(embeddings)
        report.checks.append(emb_struct_check)
        if not emb_struct_check.passed:
            report.errors.append(emb_struct_check.message)

    # Chroma validation
    chroma_count = 0
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(DATA_CHROMA))
        collection = client.get_or_create_collection("mutual_fund_chunks")
        chroma_count = collection.count()
        chroma_check = schema_validator.validate_chroma(chroma_count, manifest)
        report.checks.append(chroma_check)
        if not chroma_check.passed:
            report.errors.append(chroma_check.message)
    except Exception as e:
        chroma_check = CheckResult(
            name="chroma_validation",
            passed=False,
            message=f"Chroma access failed: {e}",
        )
        report.checks.append(chroma_check)
        report.errors.append(chroma_check.message)

    # SQLite validation
    db_path = DATA_STRUCTURED / "facts.db"
    sqlite_check = schema_validator.validate_sqlite(db_path, manifest)
    report.checks.append(sqlite_check)
    if not sqlite_check.passed:
        report.errors.append(sqlite_check.message)

    # ------------------------------------------------------------------
    # 3. Coverage check
    # ------------------------------------------------------------------
    if not report.errors:
        coverage_check = coverage_checker.check(manifest, embeddings, db_path)
        report.checks.append(coverage_check)
        if not coverage_check.passed:
            report.errors.append(coverage_check.message)

    # ------------------------------------------------------------------
    # 4. Hash verification / integrity
    # ------------------------------------------------------------------
    if embeddings:
        integrity_check, hash_str = integrity_checker.verify_embeddings(embeddings)
        report.checks.append(integrity_check)
        report.embeddings_hash = hash_str
        if not integrity_check.passed:
            report.errors.append(integrity_check.message)

    # ------------------------------------------------------------------
    # 5. Determine pass/fail
    # ------------------------------------------------------------------
    report.passed = len(report.errors) == 0
    report.summary = {
        "total_checks": len(report.checks),
        "passed_checks": sum(1 for c in report.checks if c.passed),
        "failed_checks": sum(1 for c in report.checks if not c.passed),
        "errors": report.errors,
    }

    logger.info(
        f"Validation {'PASSED' if report.passed else 'FAILED'}: "
        f"{report.summary['passed_checks']}/{report.summary['total_checks']} checks passed"
    )

    # ------------------------------------------------------------------
    # 6. Atomic index swap (only on pass)
    # ------------------------------------------------------------------
    if report.passed:
        swap_ok, swap_msg = swapper.swap(report.run_id, report.embeddings_hash)
        if swap_ok:
            report.summary["swap_status"] = swap_msg
            swapper.cleanup_old_backups(BACKUP_RETENTION_DAYS)
        else:
            report.errors.append(f"Index swap failed: {swap_msg}")
            report.passed = False
    else:
        report.summary["swap_status"] = "SKIPPED (validation failed)"
        logger.warning("Index swap skipped due to validation failure")

    # ------------------------------------------------------------------
    # 7. Audit log
    # ------------------------------------------------------------------
    audit_path = auditor.log(report)
    report.summary["audit_log"] = str(audit_path)

    logger.info("=" * 60)
    logger.info(
        f"Phase 0.6 complete: {'PASSED' if report.passed else 'FAILED'}"
    )
    logger.info("=" * 60)

    return report


if __name__ == "__main__":
    report = run_validate_phase()
    sys.exit(0 if report.passed else 1)
