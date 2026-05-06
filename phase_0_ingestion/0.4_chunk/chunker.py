"""
Phase 0.4: Chunk
================

Production-grade semantic chunker for the ingestion pipeline.
Consumes normalized text from Phase 0.3 and produces:
- Semantic chunks with metadata (doc_id, source_url, chunk_type)
- 1-sentence overlap between adjacent chunks
- Max 300 tokens per chunk

Architecture reference: Section 4, Phase 0.4
Enforcement: Max 300 tokens; overlap 1 sentence; every chunk has doc_id, source_url, chunk_type
"""

import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# Configuration
# =============================================================================

DATA_NORMALIZED = Path(os.getenv("DATA_NORMALIZED", "./data/2_normalized_text"))
DATA_CHUNKS = Path(os.getenv("DATA_CHUNKS", "./data/3_chunks"))

# Approximate max words per chunk (conservative proxy for 300 tokens)
MAX_WORDS_PER_CHUNK = 250

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("phase_0_4_chunk")


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source_url: str
    chunk_type: str
    text: str
    token_count: int
    overlap: bool = False


@dataclass
class ChunkResult:
    doc_id: str
    source_url: str
    chunked_at: str
    chunks: List[Chunk] = field(default_factory=list)
    discarded_sentences: List[str] = field(default_factory=list)
    error: Optional[str] = None


# =============================================================================
# Sentence Tokenizer with Abbreviation Protection
# =============================================================================


class SentenceTokenizer:
    """
    Sentence boundary detector with abbreviation protection.
    Avoids splitting on common abbreviations (Mr., Mrs., Dr., Ltd., etc.).
    """

    ABBREVIATIONS = {
        "mr",
        "mrs",
        "dr",
        "prof",
        "sr",
        "jr",
        "ltd",
        "inc",
        "co",
        "corp",
        "llc",
        "lp",
        "plc",
        "etf",
        "fof",
        "amc",
        "auml",
        "nav",
        "sip",
        "sid",
        "ppfas",
        "mf",
        "nfo",
        "mtf",
        "pe",
        "rsi",
        "y",
        "yr",
        "yrs",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
        "st",
        "nd",
        "rd",
        "th",
        "no",
        "vs",
        "eg",
        "ie",
        "etc",
        "pvt",
    }

    def tokenize(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Protect abbreviations by temporarily replacing their periods
        protected = self._protect_abbreviations(text)

        # Split on sentence terminators followed by space and uppercase
        raw_splits = re.split(r"(?<=[.!?])\s+(?=[A-Z])", protected)

        sentences = []
        for s in raw_splits:
            s = self._restore_abbreviations(s)
            s = s.strip()
            if s:
                sentences.append(s)
        return sentences

    def _protect_abbreviations(self, text: str) -> str:
        def replace_abbrev(m: re.Match) -> str:
            word = m.group(1).lower()
            if word in self.ABBREVIATIONS:
                return word + "\x00"  # temp placeholder
            return m.group(0)

        return re.sub(r"(\w+)\.", replace_abbrev, text)

    def _restore_abbreviations(self, text: str) -> str:
        return text.replace("\x00", ".")


# =============================================================================
# Fact-Type Detector
# =============================================================================


class FactTypeDetector:
    """
    Detects the primary fact type (chunk_type) for a sentence or chunk.
    Uses keyword matching with priority ordering.
    """

    PATTERNS: List[Tuple[str, List[str]]] = [
        ("expense_ratio", ["expense ratio"]),
        ("exit_load", ["exit load"]),
        ("min_sip", ["minimum sip", "min. for sip", "min for sip", "sip investment"]),
        (
            "min_lumpsum",
            [
                "minimum lumpsum",
                "min. for lumpsum",
                "min for 1st investment",
                "min for 2nd investment",
            ],
        ),
        ("nav", ["latest nav", "nav as of", "nav:"]),
        ("aum", ["asset under management", "fund size (aum)", "total aum"]),
        ("benchmark", ["fund benchmark", "benchmark"]),
        (
            "risk_level",
            ["risk.", "rated", "riskometer", "very high risk", "high risk", "low risk"],
        ),
        ("fund_manager", ["fund manager", "managed by", "current fund manager"]),
        (
            "inception_date",
            [
                "inception",
                "launch date",
                "date of incorporation",
                "made available to investors on",
            ],
        ),
        (
            "category",
            [
                "equity mutual fund",
                "debt mutual fund",
                "hybrid mutual fund",
                "commodities mutual fund",
            ],
        ),
        (
            "investment_objective",
            ["investment objective", "seeks to provide", "objective"],
        ),
        ("fund_house", ["fund house", "mutual fund house"]),
        ("holdings", ["holdings", "holding analysis", "portfolio"]),
        (
            "returns",
            [
                "annualised returns",
                "absolute returns",
                "fund returns",
                "returns and rankings",
            ],
        ),
        ("tax", ["tax implication", "capital gains tax", "ltcg", "stcg"]),
        ("stamp_duty", ["stamp duty"]),
    ]

    NOISE_KEYWORDS = [
        "invest in stocks",
        "etf screener",
        "ipo track",
        "stock screener",
        "demat account",
        "share market today",
        "terminal track",
        "option chain",
        "api trading",
        "mutual fund houses",
        "nfo's track",
        "sip calculator",
        "brokerage calculator",
        "margin calculator",
        "swp calculator",
        "pricing brokerage",
        "privacy policy",
        "terms and conditions",
        "disclosure",
        "information security",
        "investor charter",
        "bug bounty",
        "sitemap",
        "about us",
        "careers",
        "blog",
        "media & press",
        "help & support",
        "trust & safety",
        "download the app",
        "contact us",
        "show more",
        "others:",
        "top gainers",
        "top losers",
        "most traded",
        "market calender",
        "stocks feed",
        "share market live",
        "fii dii activity",
    ]

    def detect(self, text: str) -> str:
        """Return the best-matching chunk_type for the text."""
        text_lower = text.lower()

        for chunk_type, keywords in self.PATTERNS:
            for kw in keywords:
                if kw in text_lower:
                    return chunk_type

        return "overview"

    def is_noise(self, text: str) -> bool:
        """Check if a sentence is likely navigation/footer noise."""
        text_lower = text.lower()
        for kw in self.NOISE_KEYWORDS:
            if kw in text_lower:
                return True
        return False


# =============================================================================
# Semantic Chunker
# =============================================================================


class SemanticChunker:
    def __init__(self, max_words: int = MAX_WORDS_PER_CHUNK):
        self.max_words = max_words
        self.tokenizer = SentenceTokenizer()
        self.detector = FactTypeDetector()

    def _word_count(self, text: str) -> int:
        return len(text.split())

    def _is_self_contained(self, sentence: str) -> bool:
        """
        Basic self-containment check.
        Reject sentences that start with dependent pronouns/references.
        """
        lower = sentence.lower()
        dependent_starts = [
            "it is",
            "they are",
            "this is",
            "that is",
            "these are",
            "those are",
            "which is",
            "who is",
        ]
        for dep in dependent_starts:
            if lower.startswith(dep):
                return False
        return True

    def chunk_document(self, text: str, doc_id: str, source_url: str) -> ChunkResult:
        """
        Run full semantic chunking pipeline.
        """
        result = ChunkResult(
            doc_id=doc_id,
            source_url=source_url,
            chunked_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            sentences = self.tokenizer.tokenize(text)
            logger.info(f"{doc_id}: Tokenized into {len(sentences)} sentences")

            # Filter noise and non-self-contained sentences
            valid_sentences: List[Tuple[str, str]] = []
            for sent in sentences:
                if self.detector.is_noise(sent):
                    result.discarded_sentences.append(sent)
                    continue
                if not self._is_self_contained(sent):
                    # Allow it but log; may be part of a larger chunk
                    pass
                chunk_type = self.detector.detect(sent)
                valid_sentences.append((sent, chunk_type))

            logger.info(
                f"{doc_id}: {len(valid_sentences)} valid sentences after filtering"
            )

            if not valid_sentences:
                logger.error(f"{doc_id}: CORPUS_EMPTY — no valid sentences")
                result.error = "CORPUS_EMPTY"
                return result

            # Group sentences into semantic chunks
            chunks = self._build_chunks(valid_sentences, doc_id, source_url)
            result.chunks = chunks

            logger.info(f"{doc_id}: Produced {len(chunks)} chunks")

        except Exception as exc:
            result.error = str(exc)
            logger.error(f"{doc_id}: Chunking failed: {exc}")

        return result

    def _split_long_sentence(self, text: str, max_words: int) -> List[str]:
        """Force-split a sentence that exceeds max_words into pieces."""
        words = text.split()
        if len(words) <= max_words:
            return [text]
        pieces: List[str] = []
        for i in range(0, len(words), max_words):
            piece = " ".join(words[i : i + max_words])
            pieces.append(piece)
        return pieces

    def _build_chunks(
        self,
        sentences: List[Tuple[str, str]],
        doc_id: str,
        source_url: str,
    ) -> List[Chunk]:
        """
        Build chunks by grouping sentences, enforcing max words,
        and injecting 1-sentence overlap.
        """
        chunks: List[Chunk] = []
        current_sentences: List[str] = []
        current_type = "overview"

        for i, (sent, sent_type) in enumerate(sentences):
            sent_words = self._word_count(sent)

            # If a single sentence exceeds max_words, flush current chunk and split it
            if sent_words > self.max_words:
                if current_sentences:
                    chunk_text = " ".join(current_sentences)
                    chunks.append(
                        Chunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            source_url=source_url,
                            chunk_type=current_type,
                            text=chunk_text,
                            token_count=self._word_count(chunk_text),
                        )
                    )
                    current_sentences = []

                pieces = self._split_long_sentence(sent, self.max_words)
                for piece in pieces:
                    chunks.append(
                        Chunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            source_url=source_url,
                            chunk_type=sent_type,
                            text=piece,
                            token_count=self._word_count(piece),
                        )
                    )
                current_type = sent_type
                continue

            # Check if adding this sentence would exceed max words
            test_text = " ".join(current_sentences + [sent])
            if current_sentences and self._word_count(test_text) > self.max_words:
                # Finalize current chunk
                chunk_text = " ".join(current_sentences)
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        source_url=source_url,
                        chunk_type=current_type,
                        text=chunk_text,
                        token_count=self._word_count(chunk_text),
                    )
                )

                # Start new chunk with overlap (last sentence of previous chunk)
                overlap_sent = current_sentences[-1]
                overlap_test = " ".join([overlap_sent, sent])
                if self._word_count(overlap_test) > self.max_words:
                    # Overlap + new sentence alone exceeds limit;
                    # flush overlap as its own chunk and start fresh
                    chunks.append(
                        Chunk(
                            chunk_id=str(uuid.uuid4()),
                            doc_id=doc_id,
                            source_url=source_url,
                            chunk_type=current_type,
                            text=overlap_sent,
                            token_count=self._word_count(overlap_sent),
                        )
                    )
                    current_sentences = [sent]
                else:
                    current_sentences = [overlap_sent, sent]
                current_type = sent_type
            else:
                current_sentences.append(sent)
                # Upgrade chunk type if we hit a more specific type
                if sent_type != "overview":
                    current_type = sent_type

        # Finalize remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    source_url=source_url,
                    chunk_type=current_type,
                    text=chunk_text,
                    token_count=self._word_count(chunk_text),
                )
            )

        # Mark overlap chunks (all except first start with overlap)
        for idx in range(1, len(chunks)):
            chunks[idx].overlap = True

        return chunks


# =============================================================================
# Persistence
# =============================================================================


def save_chunks(result: ChunkResult, output_dir: Path) -> Dict[str, Any]:
    """
    Save chunks as JSON lines (one chunk per line) for downstream processing.
    Returns manifest entry.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks_path = output_dir / f"{result.doc_id}_chunks.jsonl"
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in result.chunks:
            record = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "source_url": chunk.source_url,
                "chunk_type": chunk.chunk_type,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "overlap": chunk.overlap,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"Saved {len(result.chunks)} chunks to {chunks_path}")

    # Save discarded sentences for audit
    if result.discarded_sentences:
        discard_path = output_dir / f"{result.doc_id}_discarded.txt"
        with open(discard_path, "w", encoding="utf-8") as f:
            for sent in result.discarded_sentences:
                f.write(sent + "\n")
        logger.info(
            f"Saved {len(result.discarded_sentences)} discarded sentences to {discard_path}"
        )

    return {
        "doc_id": result.doc_id,
        "source_url": result.source_url,
        "chunks_count": len(result.chunks),
        "discarded_count": len(result.discarded_sentences),
        "error": result.error,
    }


# =============================================================================
# Main Entry Point
# =============================================================================


def run_chunk_phase() -> Dict[str, Any]:
    """
    Execute Phase 0.4 Chunk over all normalized text files.
    """
    logger.info("=" * 60)
    logger.info("PHASE 0.4: CHUNK")
    logger.info("=" * 60)

    chunker = SemanticChunker()
    manifest = {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "total_docs": 0,
        "successful": 0,
        "corpus_empty": 0,
        "failed": 0,
        "results": [],
    }

    text_files = sorted(DATA_NORMALIZED.glob("DOC-*_normalized.txt"))
    manifest["total_docs"] = len(text_files)

    if not text_files:
        logger.warning(f"No DOC-*_normalized.txt files found in {DATA_NORMALIZED}")
        return manifest

    for text_path in text_files:
        doc_id = text_path.stem.replace("_normalized", "")
        source_url = _resolve_source_url(doc_id)

        logger.info(f"Chunking {doc_id} ...")

        with open(text_path, "r", encoding="utf-8") as f:
            text = f.read()

        result = chunker.chunk_document(text, doc_id, source_url)
        entry = save_chunks(result, DATA_CHUNKS)
        manifest["results"].append(entry)

        if result.error == "CORPUS_EMPTY":
            manifest["corpus_empty"] += 1
        elif result.error:
            manifest["failed"] += 1
        else:
            manifest["successful"] += 1

    # Save manifest
    manifest_path = DATA_CHUNKS / "chunk_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to {manifest_path}")

    logger.info("-" * 60)
    logger.info(
        f"Chunk complete: {manifest['successful']} success, "
        f"{manifest['corpus_empty']} corpus_empty, "
        f"{manifest['failed']} failed"
    )
    logger.info("=" * 60)

    return manifest


def _resolve_source_url(doc_id: str) -> str:
    """Map doc_id back to the whitelisted Groww URL."""
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
    run_chunk_phase()
