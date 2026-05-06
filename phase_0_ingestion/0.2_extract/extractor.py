"""
Phase 0.2: Extract
==================

Production-grade HTML extractor for the ingestion pipeline.
Parses raw HTML from Groww mutual fund pages to produce:
- Structured facts (JSON) with confidence tags
- Raw visible text fallback

Architecture reference: Section 4, Phase 0.2
Enforcement: Confidence tagging (HIGH/MEDIUM/LOW); no external links followed
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

# =============================================================================
# Configuration
# =============================================================================

DATA_RAW_HTML = Path(os.getenv("DATA_RAW_HTML", "./data/0_raw_html"))
DATA_EXTRACTED = Path(os.getenv("DATA_EXTRACTED", "./data/1_extracted_facts"))

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("phase_0_2_extract")


# =============================================================================
# Data Models
# =============================================================================


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ExtractedFact:
    fact_type: str
    value: str
    raw_snippet: str
    confidence: Confidence
    source: str  # "regex", "css_selector", "heuristic"


@dataclass
class ExtractionResult:
    doc_id: str
    source_url: str
    extracted_at: str
    structured_facts: List[ExtractedFact] = field(default_factory=list)
    raw_text: str = ""
    extraction_success: bool = False
    fallback_to_raw: bool = False
    error: Optional[str] = None


# =============================================================================
# Fact Extraction Patterns
# =============================================================================

# Each pattern: (fact_type, regex, confidence, source)
# Order matters: more specific patterns first.
FACT_PATTERNS: List[tuple] = [
    # HIGH confidence: explicitly labeled numeric facts
    (
        "expense_ratio",
        re.compile(r"Expense ratio\s+([0-9.]+)%"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "nav",
        re.compile(r"Latest NAV as of \d+ \w+ \d+ is ₹([0-9,.]+)"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "aum",
        re.compile(r"Asset Under Management\(AUM\) of ₹([0-9,.]+)\s*Cr"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "fund_size_cr",
        re.compile(r"Fund size \(AUM\)\s*₹?([0-9,.]+)\s*Cr"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "min_sip",
        re.compile(r"Minimum SIP Investment is set to ₹([0-9,.]+)"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "min_lumpsum",
        re.compile(r"Minimum Lumpsum Investment is ₹([0-9,.]+)"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "exit_load",
        re.compile(r"Exit load of ([0-9.]+%)(?:,\s*if redeemed within\s*([^.;]+))?"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "benchmark",
        re.compile(r"Fund benchmark\s+([A-Za-z0-9\s\-]+?)(?:\s+Scheme Information|$)"),
        Confidence.HIGH,
        "regex",
    ),
    (
        "fund_house",
        re.compile(
            r"Fund house\s+([A-Za-z][A-Za-z\s]+?)(?:\s+Rank\s+\(total assets\)|$)"
        ),
        Confidence.HIGH,
        "regex",
    ),
    (
        "total_aum",
        re.compile(r"Total AUM\s*₹?([0-9,.]+)\s*Cr"),
        Confidence.HIGH,
        "regex",
    ),
    # MEDIUM confidence: descriptive paragraph facts
    (
        "inception_date",
        re.compile(r"available to investors on (\d{1,2}\s+[A-Za-z]{3}\s+\d{4})"),
        Confidence.MEDIUM,
        "regex",
    ),
    (
        "fund_manager",
        re.compile(r"([A-Z][a-zA-Z\s]+) is the Current Fund Manager"),
        Confidence.MEDIUM,
        "regex",
    ),
    (
        "risk_level",
        re.compile(r"rated ([A-Za-z\s]+?) risk"),
        Confidence.MEDIUM,
        "regex",
    ),
    (
        "category",
        re.compile(r"is a ([A-Za-z\s]+) Scheme launched by"),
        Confidence.MEDIUM,
        "regex",
    ),
    # LOW confidence: heuristic / broader patterns
    (
        "investment_objective",
        re.compile(r"Investment Objective\s+([^.]{20,300}\.)"),
        Confidence.LOW,
        "heuristic",
    ),
]


# =============================================================================
# HTML Parser & Extractor
# =============================================================================


class HTMLExtractor:
    """
    Parses minified HTML from Groww mutual fund pages.
    Extracts structured facts via regex on visible text.
    Falls back to raw text if structured extraction fails.
    """

    def __init__(self):
        self.fallback_threshold = 2  # Need at least 2 HIGH facts to count as success

    def _parse_html(self, html: str) -> BeautifulSoup:
        """DOM parsing with html.parser."""
        return BeautifulSoup(html, "html.parser")

    def _extract_raw_text(self, soup: BeautifulSoup) -> str:
        """
        Raw visible text extraction.
        Strips scripts, styles, and navigation noise.
        """
        # Remove non-content tags
        for tag_name in ["script", "style", "nav", "footer", "header", "aside"]:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Get visible text with line breaks for structure
        text = soup.get_text(separator="\n", strip=True)

        # Collapse excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)

    def _extract_facts(self, raw_text: str) -> List[ExtractedFact]:
        """
        Regex field parsing against visible text.
        Each match is tagged with confidence.
        """
        facts: List[ExtractedFact] = []
        seen_types: set = set()

        for fact_type, pattern, confidence, source in FACT_PATTERNS:
            # Only take the first (most specific) match per fact_type
            if fact_type in seen_types:
                continue

            match = pattern.search(raw_text)
            if match:
                # Build value from groups
                groups = [g.strip() for g in match.groups() if g]
                value = " ".join(groups)

                # Post-process known types
                value = self._normalize_value(fact_type, value, match)

                fact = ExtractedFact(
                    fact_type=fact_type,
                    value=value,
                    raw_snippet=match.group(0),
                    confidence=confidence,
                    source=source,
                )
                facts.append(fact)
                seen_types.add(fact_type)

        return facts

    def _normalize_value(self, fact_type: str, value: str, match: re.Match) -> str:
        """Normalize extracted values for consistency."""
        if fact_type in ("nav", "min_sip", "min_lumpsum"):
            # Strip trailing punctuation
            value = value.rstrip(".,; ")
            if not value.startswith("₹"):
                value = f"₹{value}"
        elif fact_type == "aum":
            value = value.rstrip(".,; ")
            if not value.startswith("₹"):
                value = f"₹{value}"
            if "Cr" not in value:
                value = f"{value} Cr"
        elif fact_type == "expense_ratio":
            if not value.endswith("%"):
                value = f"{value}%"
        elif fact_type == "exit_load":
            # Reconstruct exit load sentence
            groups = match.groups()
            if len(groups) >= 2 and groups[1]:
                value = f"Exit load of {groups[0]}, if redeemed within {groups[1]}"
            else:
                value = f"Exit load of {groups[0]}"
        elif fact_type == "benchmark":
            # Stop at known boundary words
            for boundary in ("Scheme Information", "Fund house", "Rank"):
                if boundary in value:
                    value = value.split(boundary)[0].strip()
        elif fact_type == "fund_house":
            for boundary in ("Rank", "Total AUM"):
                if boundary in value:
                    value = value.split(boundary)[0].strip()
        elif fact_type == "risk_level":
            value = value.strip()
        return value

    def _has_external_links(self, soup: BeautifulSoup) -> bool:
        """Check for external links (informational only; we don't follow them)."""
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "groww.in" not in href:
                return True
        return False

    def extract(self, html: str, doc_id: str, source_url: str) -> ExtractionResult:
        """
        Main extraction pipeline.
        Sub-phases: DOM parsing → regex field parsing → raw visible text extraction
        """
        result = ExtractionResult(
            doc_id=doc_id,
            source_url=source_url,
            extracted_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            soup = self._parse_html(html)
            raw_text = self._extract_raw_text(soup)
            facts = self._extract_facts(raw_text)

            high_confidence_count = sum(
                1 for f in facts if f.confidence == Confidence.HIGH
            )

            # Determine if structured extraction succeeded
            if high_confidence_count >= self.fallback_threshold:
                result.structured_facts = facts
                result.raw_text = raw_text
                result.extraction_success = True
                result.fallback_to_raw = False
                logger.info(
                    f"{doc_id}: Structured extraction succeeded "
                    f"({len(facts)} facts, {high_confidence_count} HIGH)"
                )
            else:
                # Fallback to raw text only
                result.structured_facts = facts  # Keep whatever we found
                result.raw_text = raw_text
                result.extraction_success = False
                result.fallback_to_raw = True
                logger.warning(
                    f"{doc_id}: Structured extraction insufficient "
                    f"({high_confidence_count} HIGH facts). Falling back to raw text."
                )

        except Exception as exc:
            result.error = str(exc)
            result.extraction_success = False
            result.fallback_to_raw = True
            logger.error(f"{doc_id}: Extraction failed: {exc}")

        return result


# =============================================================================
# Persistence
# =============================================================================


def save_extraction(result: ExtractionResult, output_dir: Path) -> Dict[str, Any]:
    """
    Save extraction result as JSON facts + raw text file.
    Returns manifest entry.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save structured facts JSON
    facts_data = [
        {
            "fact_type": f.fact_type,
            "value": f.value,
            "confidence": f.confidence.value,
            "source": f.source,
            "raw_snippet": f.raw_snippet,
        }
        for f in result.structured_facts
    ]

    facts_path = output_dir / f"{result.doc_id}_facts.json"
    with open(facts_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "doc_id": result.doc_id,
                "source_url": result.source_url,
                "extracted_at": result.extracted_at,
                "extraction_success": result.extraction_success,
                "fallback_to_raw": result.fallback_to_raw,
                "error": result.error,
                "facts": facts_data,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    logger.info(f"Saved structured facts: {facts_path}")

    # Save raw text
    raw_path = output_dir / f"{result.doc_id}_raw.txt"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(result.raw_text)
    logger.info(f"Saved raw text: {raw_path}")

    return {
        "doc_id": result.doc_id,
        "source_url": result.source_url,
        "extraction_success": result.extraction_success,
        "fallback_to_raw": result.fallback_to_raw,
        "facts_count": len(result.structured_facts),
        "high_confidence_count": sum(
            1 for f in result.structured_facts if f.confidence == Confidence.HIGH
        ),
        "error": result.error,
    }


# =============================================================================
# Main Entry Point
# =============================================================================


def run_extract_phase() -> Dict[str, Any]:
    """
    Execute Phase 0.2 Extract over all raw HTML files.
    Returns manifest dict.
    """
    logger.info("=" * 60)
    logger.info("PHASE 0.2: EXTRACT")
    logger.info("=" * 60)

    extractor = HTMLExtractor()
    manifest = {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "total_docs": 0,
        "successful": 0,
        "fallback_to_raw": 0,
        "failed": 0,
        "results": [],
    }

    html_files = sorted(DATA_RAW_HTML.glob("DOC-*.html"))
    manifest["total_docs"] = len(html_files)

    if not html_files:
        logger.warning(f"No DOC-*.html files found in {DATA_RAW_HTML}")
        return manifest

    for html_path in html_files:
        doc_id = html_path.stem
        # Derive source_url from fetcher whitelist mapping
        # We use a simple heuristic: read the HTML title or assume standard URL
        source_url = _resolve_source_url(doc_id)

        logger.info(f"Extracting {doc_id} ...")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        result = extractor.extract(html, doc_id, source_url)
        entry = save_extraction(result, DATA_EXTRACTED)
        manifest["results"].append(entry)

        if result.extraction_success:
            manifest["successful"] += 1
        elif result.fallback_to_raw:
            manifest["fallback_to_raw"] += 1
        else:
            manifest["failed"] += 1

    # Save manifest
    manifest_path = DATA_EXTRACTED / "extract_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to {manifest_path}")

    logger.info("-" * 60)
    logger.info(
        f"Extract complete: {manifest['successful']} success, "
        f"{manifest['fallback_to_raw']} fallback, "
        f"{manifest['failed']} failed"
    )
    logger.info("=" * 60)

    return manifest


def _resolve_source_url(doc_id: str) -> str:
    """Map doc_id back to the whitelisted Groww URL."""
    # Reconstruct whitelist (must match fetcher.py)
    whitelisted = [
        "https://groww.in/mutual-funds/the-wealth-company-small-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-ethical-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-multi-asset-allocation-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-flexi-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-gold-etf-fof-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-liquid-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-arbitrage-fund-direct-growth",
    ]
    try:
        idx = int(doc_id.split("-")[1]) - 1
        return whitelisted[idx]
    except (IndexError, ValueError):
        return ""


if __name__ == "__main__":
    run_extract_phase()
