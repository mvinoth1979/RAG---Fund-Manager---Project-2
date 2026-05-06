import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Setup paths and env
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv()

from phase_1_query_sanitization.phase_1_runner import run_phase_1
from phase_2_corpus_retrieval.phase_2_orchestrator import run_phase_2
from phase_3_context_assembly.pipeline import ContextAssemblyPipeline
from phase_4_response_generation.generator import ResponseGenerator
from phase_5_compliance_validation.pipeline import CompliancePipeline

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("api")

app = FastAPI(title="Mutual Fund RAG Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    text: str
    source_url: Optional[str] = None
    footer_date: str
    terminal_state: str

# Config
WHITELISTED_URLS = os.getenv("WHITELISTED_URLS", "").split(",")
if not WHITELISTED_URLS or WHITELISTED_URLS == [""]:
    WHITELISTED_URLS = [
        "https://groww.in/mutual-funds/the-wealth-company-small-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-ethical-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-multi-asset-allocation-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-flexi-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-gold-etf-fof-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-liquid-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-arbitrage-fund-direct-growth",
    ]

# Global pipelines
context_pipeline = ContextAssemblyPipeline(whitelist=WHITELISTED_URLS)
generation_pipeline = ResponseGenerator()
banned_phrases_path = str(PROJECT_ROOT / "phase_5_compliance_validation" / "5.1_advisory_detection" / "banned_phrases.json")
compliance_pipeline = CompliancePipeline(banned_phrases_path=banned_phrases_path)

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "Mutual Fund RAG Assistant API is running.",
        "endpoints": ["/api/chat (POST)"]
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: QueryRequest):
    query = request.query
    logger.info(f"Received query: {query}")

    # Phase 1: Query Sanitization & Classification
    p1_result = run_phase_1(query)
    logger.info(f"Phase 1 result: {p1_result}")

    if p1_result["blocked_by_pii"] or p1_result["terminal_response"]:
        res = p1_result["terminal_response"]
        return ChatResponse(
            text=res["text"],
            source_url=res["source_url"],
            footer_date=res["footer_date"],
            terminal_state=res["terminal_state"]
        )

    # Phase 2: Corpus Retrieval
    p2_result = run_phase_2(p1_result["sanitized_query"])
    if not p2_result.filtered_candidates:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return ChatResponse(
            text="I do not have that information in my current sources.",
            source_url=None,
            footer_date=today,
            terminal_state="T3"
        )

    # Phase 3: Context Assembly
    context_string, source_url, doc_id = context_pipeline.execute(p2_result.filtered_candidates)
    if not context_string:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return ChatResponse(
            text="I do not have that information in my current sources.",
            source_url=None,
            footer_date=today,
            terminal_state="T3"
        )

    # Phase 4: Response Generation
    p4_result = generation_pipeline.generate_response(context_string, p1_result["sanitized_query"])
    
    # Phase 5: Compliance Check
    p5_result = compliance_pipeline.validate(
        raw_response=p4_result.text,
        source_context=context_string,
        source_url=source_url
    )

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return ChatResponse(
        text=p5_result.response,
        source_url=source_url,
        footer_date=today,
        terminal_state=p5_result.status
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
