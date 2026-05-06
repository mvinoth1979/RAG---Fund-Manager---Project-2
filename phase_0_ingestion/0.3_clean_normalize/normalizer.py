"""
Phase 0.3: Clean & Normalize
============================

Production-grade text normalizer for the ingestion pipeline.
Consumes structured facts + raw text from Phase 0.2 and produces:
- Normalized raw text (HTML entities decoded, Unicode NFKC, whitespace collapsed)
- Typed fact records (currency standardized, dates normalized, numbers cleaned)

Architecture reference: Section 4, Phase 0.3
Enforcement: All currency to ₹; all percentages with %; dates to YYYY-MM-DD
"""

import html
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# =============================================================================
# Configuration
# =============================================================================

DATA_EXTRACTED = Path(os.getenv("DATA_EXTRACTED", "./data/1_extracted_facts"))
DATA_NORMALIZED = Path(os.getenv("DATA_NORMALIZED", "./data/2_normalized_text"))

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("phase_0_3_normalize")


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class TypedFact:
    fact_type: str
    value: str
    confidence: str
    normalized: bool = True
    rejection_reason: Optional[str] = None


@dataclass
class NormalizeResult:
    doc_id: str
    source_url: str
    normalized_at: str
    typed_facts: List[TypedFact] = field(default_factory=list)
    normalized_text: str = ""
    rejected_facts: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


# =============================================================================
# Normalization Engine
# =============================================================================


class TextNormalizer:
    """
    Applies the normalization pipeline to raw text and structured facts.

    Sub-phases:
        1. HTML entity decode
        2. Unicode NFKC normalization
        3. Whitespace collapse
        4. Currency standardization
        5. Number normalization
        6. Date normalization
    """

    # Currency symbols that should map to ₹
    CURRENCY_SYMBOLS = re.compile(
        r"[\$\u00A2-\u00A5\u09F2\u09F3\u0AF1\u0BF9\u0E3F"
        r"\u17DB\u20A0-\u20CF\uA838\uFDFC\uFE69\uFF04\uFFE5\uFFE6]"
    )

    # Common Indian number formatting: 1,00,000 or 1,000
    INDIAN_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{2,3})+")
    STANDARD_NUMBER_RE = re.compile(r"\d{1,3}(?:,\d{3})+")

    # Date patterns
    DATE_PATTERNS = [
        # 18 Jul 2025 → 2025-07-18
        (re.compile(r"(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})"), "dd_mmm_yyyy"),
        # 2025-07-18 (already ISO)
        (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), "iso"),
    ]

    MONTH_MAP = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }

    def normalize_text(self, text: str) -> str:
        """
        Apply full normalization pipeline to free-form text.
        """
        # 1. HTML entity decode
        text = html.unescape(text)

        # 2. Unicode NFKC normalization
        text = unicodedata.normalize("NFKC", text)

        # 3. Whitespace collapse
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n", text)
        text = text.strip()

        # 4. Currency standardization
        text = self._standardize_currency(text)

        # 5. Number normalization
        text = self._normalize_numbers(text)

        return text

    def _standardize_currency(self, text: str) -> str:
        """Replace all currency symbols with ₹."""
        return self.CURRENCY_SYMBOLS.sub("₹", text)

    def _normalize_numbers(self, text: str) -> str:
        """
        Remove comma separators from numbers for consistency.
        Keeps the number as a plain digit string.
        """

        # Remove commas from standard grouped numbers
        def remove_commas(m: re.Match) -> str:
            return m.group(0).replace(",", "")

        text = self.STANDARD_NUMBER_RE.sub(remove_commas, text)
        text = self.INDIAN_NUMBER_RE.sub(remove_commas, text)
        return text

    def normalize_date(self, date_str: str) -> Optional[str]:
        """
        Convert date string to YYYY-MM-DD.
        Returns None if parsing fails.
        """
        for pattern, fmt in self.DATE_PATTERNS:
            match = pattern.search(date_str)
            if not match:
                continue

            if fmt == "iso":
                return match.group(0)

            if fmt == "dd_mmm_yyyy":
                day, month_str, year = match.groups()
                month_num = self.MONTH_MAP.get(month_str.lower().strip())
                if month_num:
                    return f"{year}-{month_num}-{int(day):02d}"

        logger.warning(f"Could not normalize date: {date_str}")
        return None

    def normalize_percentage(self, value: str) -> str:
        """Ensure percentage values end with %."""
        value = value.strip()
        if "%" not in value:
            # Try to append % if it looks like a percentage number
            if re.match(r"^[0-9]+(\.[0-9]+)?$", value):
                value = f"{value}%"
        return value

    def normalize_fact(self, fact_type: str, value: str) -> Optional[str]:
        """
        Normalize a single fact value based on its type.
        Returns None if the fact is malformed and should be rejected.
        """
        value = self.normalize_text(value)

        if fact_type == "inception_date":
            normalized = self.normalize_date(value)
            if normalized is None:
                return None
            return normalized

        if fact_type == "expense_ratio":
            return self.normalize_percentage(value)

        if fact_type in (
            "nav",
            "aum",
            "fund_size_cr",
            "min_sip",
            "min_lumpsum",
            "total_aum",
        ):
            # Ensure currency symbol presence
            if not value.startswith("₹"):
                # Try to inject ₹ if there's a number nearby
                value = re.sub(r"(^|\s)([0-9])", r"\1₹\2", value)
            return value

        if fact_type == "exit_load":
            return self.normalize_percentage(value)

        # Default: just return cleaned text
        return value


class FactValidator:
    """
    Validates normalized facts against enforcement rules.
    Rejects malformed records.
    """

    @staticmethod
    def validate(fact_type: str, normalized_value: str) -> Optional[str]:
        """
        Returns rejection reason string if invalid, None if valid.
        """
        if not normalized_value or not normalized_value.strip():
            return "Empty value after normalization"

        if fact_type == "expense_ratio":
            if "%" not in normalized_value:
                return "Percentage enforcement failed: missing %"
            if not re.search(r"[0-9]", normalized_value):
                return "No numeric value found"

        if fact_type in (
            "nav",
            "aum",
            "fund_size_cr",
            "min_sip",
            "min_lumpsum",
            "total_aum",
        ):
            if "₹" not in normalized_value:
                return "Currency enforcement failed: missing ₹"

        if fact_type == "inception_date":
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", normalized_value):
                return "Date enforcement failed: not YYYY-MM-DD"

        return None


# =============================================================================
# Pipeline Runner
# =============================================================================


class NormalizePipeline:
    def __init__(self):
        self.normalizer = TextNormalizer()
        self.validator = FactValidator()

    def run(self, facts_json: Dict[str, Any], raw_text: str) -> NormalizeResult:
        """
        Run full clean & normalize pipeline on one document.
        """
        doc_id = facts_json.get("doc_id", "UNKNOWN")
        source_url = facts_json.get("source_url", "")

        result = NormalizeResult(
            doc_id=doc_id,
            source_url=source_url,
            normalized_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # Normalize raw text
            result.normalized_text = self.normalizer.normalize_text(raw_text)

            # Normalize and validate each structured fact
            for fact in facts_json.get("facts", []):
                fact_type = fact.get("fact_type", "")
                original_value = fact.get("value", "")
                confidence = fact.get("confidence", "LOW")

                normalized_value = self.normalizer.normalize_fact(
                    fact_type, original_value
                )

                if normalized_value is None:
                    result.rejected_facts.append(
                        {
                            "fact_type": fact_type,
                            "original_value": original_value,
                            "rejection_reason": "Normalization failed",
                        }
                    )
                    logger.warning(
                        f"{doc_id}: Rejected fact '{fact_type}' — normalization failed"
                    )
                    continue

                rejection_reason = self.validator.validate(fact_type, normalized_value)
                if rejection_reason:
                    result.rejected_facts.append(
                        {
                            "fact_type": fact_type,
                            "original_value": original_value,
                            "normalized_value": normalized_value,
                            "rejection_reason": rejection_reason,
                        }
                    )
                    logger.warning(
                        f"{doc_id}: Rejected fact '{fact_type}' — {rejection_reason}"
                    )
                    continue

                typed_fact = TypedFact(
                    fact_type=fact_type,
                    value=normalized_value,
                    confidence=confidence,
                    normalized=True,
                )
                result.typed_facts.append(typed_fact)

            logger.info(
                f"{doc_id}: Normalized {len(result.typed_facts)} facts, "
                f"rejected {len(result.rejected_facts)}"
            )

        except Exception as exc:
            result.error = str(exc)
            logger.error(f"{doc_id}: Normalization pipeline failed: {exc}")

        return result


# =============================================================================
# Persistence
# =============================================================================


def save_normalized(result: NormalizeResult, output_dir: Path) -> Dict[str, Any]:
    """
    Save normalized result:
    - {doc_id}_typed_facts.json
    - {doc_id}_normalized.txt
    Returns manifest entry.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save typed facts JSON
    facts_data = [
        {
            "fact_type": f.fact_type,
            "value": f.value,
            "confidence": f.confidence,
            "normalized": f.normalized,
        }
        for f in result.typed_facts
    ]

    facts_path = output_dir / f"{result.doc_id}_typed_facts.json"
    with open(facts_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "doc_id": result.doc_id,
                "source_url": result.source_url,
                "normalized_at": result.normalized_at,
                "typed_facts": facts_data,
                "rejected_facts": result.rejected_facts,
                "error": result.error,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"Saved typed facts: {facts_path}")

    # Save normalized text
    text_path = output_dir / f"{result.doc_id}_normalized.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(result.normalized_text)
    logger.info(f"Saved normalized text: {text_path}")

    return {
        "doc_id": result.doc_id,
        "source_url": result.source_url,
        "typed_facts_count": len(result.typed_facts),
        "rejected_count": len(result.rejected_facts),
        "error": result.error,
    }


# =============================================================================
# Main Entry Point
# =============================================================================


def run_normalize_phase() -> Dict[str, Any]:
    """
    Execute Phase 0.3 Clean & Normalize over all extracted fact files.
    """
    logger.info("=" * 60)
    logger.info("PHASE 0.3: CLEAN & NORMALIZE")
    logger.info("=" * 60)

    pipeline = NormalizePipeline()
    manifest = {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "total_docs": 0,
        "successful": 0,
        "failed": 0,
        "results": [],
    }

    facts_files = sorted(DATA_EXTRACTED.glob("DOC-*_facts.json"))
    manifest["total_docs"] = len(facts_files)

    if not facts_files:
        logger.warning(f"No DOC-*_facts.json files found in {DATA_EXTRACTED}")
        return manifest

    for facts_path in facts_files:
        doc_id = facts_path.stem.replace("_facts", "")
        raw_path = DATA_EXTRACTED / f"{doc_id}_raw.txt"

        logger.info(f"Normalizing {doc_id} ...")

        # Load structured facts
        with open(facts_path, "r", encoding="utf-8") as f:
            facts_json = json.load(f)

        # Load raw text
        raw_text = ""
        if raw_path.exists():
            with open(raw_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            logger.warning(f"Raw text file missing for {doc_id}: {raw_path}")

        result = pipeline.run(facts_json, raw_text)
        entry = save_normalized(result, DATA_NORMALIZED)
        manifest["results"].append(entry)

        if result.error:
            manifest["failed"] += 1
        else:
            manifest["successful"] += 1

    # Save manifest
    manifest_path = DATA_NORMALIZED / "normalize_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to {manifest_path}")

    logger.info("-" * 60)
    logger.info(
        f"Normalize complete: {manifest['successful']} success, "
        f"{manifest['failed']} failed"
    )
    logger.info("=" * 60)

    return manifest


if __name__ == "__main__":
    run_normalize_phase()
