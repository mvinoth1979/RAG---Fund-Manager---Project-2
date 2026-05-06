# Final Production-Grade Architecture — Mutual Fund FAQ Assistant

## 1. System Overview

**Product**: Facts-only FAQ assistant for The Wealth Company mutual fund schemes  
**Data Source**: 7 Groww URLs (user-authorized override of official-source constraint)  
**Architecture**: Lightweight RAG with deterministic compliance pipeline  
**Core Principle**: *Accuracy over intelligence. Compliance over convenience.*

---

## 2. Non-Negotiable Architectural Principles

| ID | Principle | Enforcement |
|----|-----------|-------------|
| P1 | **Zero-Advice Architecture** | Pre-filter classification + post-generation validation |
| P2 | **Single Source Citation** | One whitelisted Groww URL per answer; injected by orchestrator |
| P3 | **Hallucination Elimination** | Context-bound generation; faithfulness scoring; temperature=0.0 |
| P4 | **Unknown Answer Default** | "I do not have that information" when confidence < 0.60 |
| P5 | **Determinism Over Creativity** | No paraphrasing; no tone variation; structured output preferred |

---

## 3. Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Frontend** | React 18 + TypeScript + Tailwind CSS | Lightweight, type-safe, responsive |
| **API Gateway** | FastAPI (Python) | Async-native, OpenAPI auto-generation, Pydantic validation |
| **Orchestration** | Python 3.11 + Pydantic models | Deterministic state machine, strict typing |
| **Embedding Model** | `BAAI/bge-large-en-v1.5` (1024-dim) | Higher quality semantic representations for factual retrieval |
| **Chunking Strategy** | Semantic (fact-type-driven) | Split at sentence boundaries; self-contained; max 300 tokens |
| **Cross-Encoder** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Lightweight reranking |
| **Vector Store** | Chroma DB (persistent) | Native metadata filtering, persistent storage, easy backup |
| **Structured Store** | Chroma DB metadata + SQLite (facts table) | Chroma handles vectors + metadata; SQLite for structured KV lookups |
| **LLM (Primary)** | Groq API (`llama3-8b-8192` or `mixtral-8x7b-32768`) | temperature=0.0, max_tokens=150; LPU inference for low latency |
| **LLM (Fallback 1)** | Groq API (`mixtral-8x7b-32768`) | Auto-failover on primary model timeout |
| **LLM (Fallback 2)** | Google Gemini (`gemini-1.5-flash` or `gemini-1.5-pro`) | temperature=0.0, max_tokens=150; used if Groq is unavailable |
| **LLM (Fallback 3)** | Local Ollama (`llama3.1:8b`) | Offline fallback; no API dependency |
| **Ingestion HTTP** | `httpx` + `curl_cffi` fallback | Anti-bot TLS fingerprinting |
| **Observability** | Prometheus metrics + structured JSON logs | Lightweight, industry standard |
| **Deployment** | Docker + Docker Compose | Single-command local deployment |

---

## 4. Phase-Wise Architecture

### Phase 0: Ingestion Pipeline (Offline)

### Phase 0.0: Automated Ingestion Scheduler

Runs daily or upon manual trigger to ensure the corpus is synchronized with the latest fund data from Groww.

#### 0.0.1 Trigger Logic
- **Primary**: GitHub Actions Cron Schedule (`30 4 * * *`) — equivalent to **10:00 AM IST**.
- **Secondary**: `workflow_dispatch` (Manual) — Allows developers to trigger an immediate refresh.
- **Failover**: `on: push` (limited to `data/config.json`) — Triggers refresh when fund URLs are updated.

#### 0.0.2 Full-Stack Execution Workflow
When the scheduler is invoked (Cron or Manual), it executes a sequential pipeline covering all phases:
1.  **Ingestion (Phase 0)**: Fetches, extracts, and indexes the latest fund data.
2.  **API Verification (Phases 1-6)**: 
    - Spins up a temporary FastAPI instance.
    - Runs the **Regression Test Suite** (50+ cases) to ensure intent classification and factual retrieval are still accurate with the new data.
    - **Enforcement**: If test pass rate < 95%, the deployment is aborted.
3.  **Frontend Build (Phase 7)**:
    - Executes `npm run build` for the React UI.
    - Updates static metadata (e.g., `last_sync_date`) used in the persistent disclaimer.
4.  **Atomic Deployment**: 
    - Updates the persistent volumes for Chroma DB and SQLite.
    - Restarts the Docker containers to serve the fresh build.

#### 0.0.3 Edge Cases & Error Handling
- **Scraping Failure**: If Groww layout changes, extraction confidence will drop. **Enforcement**: If >2 funds fail extraction, the entire run is aborted; the previous day's data is retained.
- **Rate Limiting**: GitHub Action IPs may be flagged. **Mitigation**: Implement exponential backoff and randomized delays in `fetcher.py`.
- **Atomic Swap**: The scheduler must verify the integrity of the new SQLite DB before finalizing the commit to prevent serving corrupted data.
- **Notification**: Failures trigger a GitHub Issue creation or an alert to the `#ingestion-alerts` channel.

#### 0.1 Fetch
| Input | 7 whitelisted Groww URLs |
| Output | Raw HTML + HTTP metadata |
| Sub-phases | ETag conditional check → HTTP fetch (anti-bot headers) → retry logic → circuit breaker |
| Enforcement | URL whitelist validation before fetch; redirects disabled; deny-all outbound except whitelist |
| Failure | Log `FETCH_FAILED`; retain previous corpus |

#### 0.2 Extract
| Input | Raw HTML |
| Output | Structured facts (JSON) + raw text |
| Sub-phases | DOM parsing → CSS selector extraction → regex field parsing → raw visible text extraction |
| Enforcement | Extracted fields tagged with confidence (HIGH/MEDIUM/LOW); no external links followed |
| Failure | Structured extraction fails → fall back to raw text only |

#### 0.3 Clean & Normalize
| Input | Structured facts + raw text |
| Output | Normalized text + typed fact records |
| Sub-phases | HTML entity decode → Unicode NFKC → whitespace collapse → currency standardization → number normalization |
| Enforcement | All currency to `₹`; all percentages with `%`; dates to `YYYY-MM-DD` |
| Failure | Malformed records rejected |

#### 0.4 Chunk
| Input | Normalized text per document |
| Output | Semantic chunks with metadata |
| Sub-phases | Fact-type detection → **semantic splitting** (sentence-boundary) → self-containment validation → overlap injection |
| Chunking Strategy | **Semantic**: each chunk covers one conceptual unit (expense ratio, exit load, etc.) |
| Enforcement | Overlap: 1 sentence between adjacent chunks to preserve cross-sentence context |
| Enforcement | Max 300 tokens per chunk; every chunk must have `doc_id`, `source_url`, `chunk_type`; chunks without metadata discarded |
| Failure | Document producing 0 chunks triggers `CORPUS_EMPTY` alert |

#### 0.5 Embed & Index
| Input | Chunks |
| Output | Vector index + structured fact DB |
| Sub-phases | Batch embedding (BGE) → L2 normalization → Chroma collection upsert → SQLite structured store load |
| Enforcement | Dimension check (must be 1024); no NaN vectors; metadata binding mandatory |
| Failure | Hash mismatch or validation error → reject record |

#### 0.6 Validate & Audit
| Input | New index + metadata |
| Output | Active/Shadow index pointer swap |
| Sub-phases | Schema validation → coverage check (all 7 docs must have chunks) → hash verification → atomic index swap |
| Enforcement | All 7 URLs must produce ≥1 chunk; old index retained 7 days for rollback |
| Failure | Validation failure → keep previous index active; alert admin

---

### Phase 1: Query Sanitization & Classification (Online)

#### 1.1 PII Detection
| Input | Raw user query string |
| Output | Sanitized query OR `PII_BLOCKED` signal |
| Logic | Regex scan for PAN, Aadhaar, account numbers, OTP, email, phone |
| Enforcement | **CRITICAL**: Any match → immediate terminal state T1; query never reaches LLM |
| False Positive Protection | Fund names whitelisted (none contain number patterns in this corpus) |

#### 1.2 Intent Classification
| Input | Sanitized query |
| Output | `FACTUAL` / `ADVISORY` / `UNCLEAR` |
| Logic | Rule-based keyword classifier (not ML) |
| Advisory Triggers | `should`, `better`, `best`, `recommend`, `safe`, `outperform`, `invest now`, `buy`, `sell` |
| Factual Triggers | `what is`, `expense ratio`, `exit load`, `minimum sip`, `benchmark`, `riskometer` |
| Enforcement | `UNCLEAR` defaults to `ADVISORY` (safe default); score ≥ 0.5 → refusal |
| Failure | Timeout → default to `ADVISORY` |

#### 1.3 Refusal Generation (Advisory Path)
| Input | `ADVISORY` or `UNCLEAR` label |
| Output | Terminal response T2 |
| Logic | Pre-approved template injection |
| Enforcement | No LLM called; response assembled by orchestrator |

---

### Phase 2: Corpus Retrieval

#### 2.1 Query Normalization (LLM-Enhanced)
| Input | Sanitized factual query |
| Output | Canonical query string |
| Sub-Phase A: Schema-Aware LLM Correction | Uses a fast LLM (Llama 3 8B) injected with the **Valid Schema** (Fund Names, Fact Types) to repair letter transpositions (NVA→NAV) and misspellings (Smal→Small) using few-shot guidance. |
| Sub-Phase B: Rule-based Normalization | Lowercase → punctuation strip → abbreviation expansion (SIP, NAV, AUM) → synonym mapping (`charges` → `expense ratio`) → fund alias canonicalization |
| Enforcement | Corrected query is passed to Phase 2.2; no learned components in Step B. |

#### 2.2 Entity / Scheme Resolution
| Input | Normalized query |
| Output | `ResolvedQuery` object |
| Logic | Extract fund aliases → map to `doc_id`; extract fact synonyms → map to `chunk_type` |
| Enforcement | Multiple fund mentions + explicit comparison → trigger advisory refusal before retrieval |
| Failure | No fund alias found → search all 7 docs; no fact type found → rely on semantic retrieval only |

#### 2.3 Hybrid Retrieval
| Input | Resolved query |
| Output | Ranked candidate chunks |
| Parallel Paths | **Dense**: BGE embedding → Chroma vector search (top-k=10, where filter `doc_id` ∈ resolved funds) → **Keyword**: BM25 on tokenized chunks → **Structured KV**: direct lookup if fact_type confidence ≥ 0.8 and single fund |
| Fusion | Reciprocal Rank Fusion (k=60) |
| Enforcement | Structured KV hit inserted at rank 1 if found |

#### 2.4 Relevance Filtering
| Input | Fused candidates |
| Output | Chunks with similarity ≥ 0.75 |
| Enforcement | Hard threshold; no "best effort" retrieval; all chunks below threshold discarded |

---

### Phase 3: Context Assembly & Source Binding

#### 3.1 Source Whitelist Validation
| Input | Filtered chunks |
| Output | Validated chunks |
| Logic | Verify every chunk's `source_url` ∈ whitelist |
| Enforcement | Any invalid chunk → discard + log security event |

#### 3.2 Single Source Selection
| Input | Validated chunks from multiple possible documents |
| Output | Chunks from exactly ONE document |
| Logic | Select document with highest-scoring chunk; tie-breaker: lowest `doc_id` |
| Enforcement | **P2**: Only one source URL per response |

#### 3.3 Context Block Assembly
| Input | Single-source chunks |
| Output | Concatenated context string + bound `source_url` + `doc_id` |
| Logic | Concatenate up to 2000 tokens; truncate at last full sentence |
| Enforcement | Context must be non-empty; `source_url` must be non-null |

---

### Phase 4: Response Generation

#### 4.1 Prompt Construction
| Input | Context block + original query |
| Output | Final prompt string |
| Template | Locked system prompt: *"You are a fact extraction engine. Use ONLY the provided context. Do not analyze, compare, recommend, or evaluate. If the answer is not in the context, respond ONLY with: 'I do not have that information in my current sources.' Answer in 1-3 sentences."* |
| Enforcement | Prompt is version-controlled; hash logged with every call |

#### 4.2 LLM Inference
| Input | Final prompt |
| Output | Raw response string |
| Parameters | `temperature=0.0`, `top_p=1.0`, `max_tokens=150`, `seed=42` |
| Provider (Primary) | Groq API (`llama3-8b-8192` preferred; `mixtral-8x7b-32768` alternative) |
| Provider (Fallback) | Google Gemini API (`gemini-1.5-flash` preferred; `gemini-1.5-pro` alternative) |
| Client (Groq) | OpenAI-compatible client (`groq` Python SDK) |
| Client (Gemini) | `google-generativeai` SDK |
| Failover Order | Groq primary → Groq secondary → Gemini → Ollama local |
| Enforcement | **P3**: No sampling; deterministic output; timeout 10 seconds |
| Latency Target | < 300ms (LPU acceleration) |

#### 4.3 Failure Handling
| Scenario | Action |
|----------|--------|
| Timeout | Return T4 (System Error) |
| Empty response | Return T3 (Unknown) |
| API failure | Return T4 (System Error) |

---

### Phase 5: Compliance Validation

#### 5.1 Advisory Language Detection
| Input | Raw LLM response |
| Output | `CLEAN` or `ADVISORY_DETECTED` |
| Logic | Case-insensitive substring match against banned phrase list |
| Categories | Prescriptive, Comparative, Evaluative, Predictive, Action-oriented, Recommendation |
| Enforcement | **P1**: Any match → discard response → return T2 (Refusal) |

#### 5.2 Hallucination / Faithfulness Check
| Input | Raw response + source context |
| Output | `FAITHFUL` or `HALLUCINATION_DETECTED` |
| Logic | Extract numbers, entities, benchmarks from response → verify existence in context |
| Enforcement | **P3**: Any untraceable claim → discard → return T3 (Unknown) |

#### 5.3 Sentence Count Validation
| Input | Raw response |
| Output | Validated text or truncation signal |
| Logic | Sentence tokenizer with abbreviation protection |
| Enforcement | **C1**: >3 sentences → safe truncate if possible; else discard → T3 |

#### 5.4 Citation Injection & Footer Append
| Input | Validated response + bound `source_url` |
| Output | Final assembled response |
| Logic | Orchestrator appends `Source: {url}` and `Last updated from sources: {date}` |
| Enforcement | **P2**: LLM never generates URL; URL must be in whitelist; refusal/unknown responses get `Source: N/A` |

---

### Phase 6: Response Delivery

| Input | Final validated response |
| Output | UI-ready payload |
| Sub-phases | HTML escaping → URL linkification → disclaimer rendering |
| Enforcement | No `dangerouslySetInnerHTML`; all external links have `rel="noopener noreferrer"` |

---

### Phase 7: UI & Frontend Development

#### 7.1 Design Philosophy & Deployment Setup
| Input | API responses from backend |
| Output | Interactive web interface |
| Technology Stack | React 18 + TypeScript + Tailwind CSS + Vite |
| Location | **Project Root** (Migrated for Vercel Zero-Config compliance) |
| Design Principles | Minimal, trust-first, accessible, mobile-first, stateless |
| Sub-phases | Root-level Vite setup → TypeScript config → Tailwind CSS → Component structure |
| Enforcement | Single-page application (SPA) with no navigation menus |

#### 7.2 Component Architecture
| Input | User interactions + API data |
| Output | Rendered UI components |
| Component Structure | App root → Header → WelcomeScreen → ChatInterface → Message components → InputArea |
| Enforcement | No `dangerouslySetInnerHTML`; all external links have `rel="noopener noreferrer"` |

**Component Hierarchy**:
```text
App
├── Header (Title + DisclaimerBadge)
├── MainContainer
│   ├── WelcomeScreen (WelcomeMessage, ExampleQuestions)
│   └── ChatInterface
│       ├── MessageList (UserMessage, AssistantMessage, SourceCitation, FooterDate)
│       └── InputArea (TextInput, SendButton, LoadingIndicator)
└── Footer (PrivacyNotice, AMFI/SEBI Links)
```

**Key Component Specifications**:
- **Header**: Height 56px (mobile)/64px (desktop). Persistent Disclaimer Badge.
- **ExampleQuestions**: Pre-defined cards (Expense ratio, Minimum SIP, Benchmark).
- **MessageBubble**: User (Blue/Right), Assistant (Gray/Left). Max width 85%.
- **SourceCitation**: Truncated domain + path. Underline on hover. `rel="noopener noreferrer"`.
- **InputArea**: Client-side validation (max 200 chars, trim whitespace). Disabled when empty.

#### 7.3 Screen States & UI Flow
- **State 1: Welcome Screen**: Shows example questions, persistent disclaimer badge. No chat history.
- **State 2: Active Chat (Factual Answer)**: Assistant message with robot icon, clickable source link, and footer date. Max 3 sentences.
- **State 3: Refusal Response**: Refusal icon (🚫). Educational link to AMFI. `Source: N/A`.
- **State 4: Unknown Answer**: Question mark icon (❓). `Source: N/A`.
- **State 5: Loading**: Skeleton loader or ellipsis. Input disabled. Timeout at 10s.
- **State 6: Error**: Warning icon (⚠️). Option to retry.

#### 7.4 State Management & API Integration
| Input | User queries + API responses |
| Output | UI state updates |
| State Management | React hooks (`useState`, `useEffect`) with in-memory component state. No persistence. |
| API Endpoint | `POST /api/query` |
| Enforcement | Rate limiting awareness; input validation; loading indicators; error handling |

**Client-Side Handling**:
| Backend `type` | UI Behavior |
|----------------|-------------|
| `answer` | Render AssistantMessage with source link |
| `refusal` | Render AssistantMessage with refusal icon + educational link |
| `unknown` | Render AssistantMessage with question mark icon |
| `error` | Render AssistantMessage with warning icon |

#### 7.5 Responsive Design & Accessibility
| Input | Component layouts |
| Output | Mobile-first responsive design |
| Breakpoints | Mobile (< 640px), Tablet (640–1024px), Desktop (> 1024px) |
| Enforcement | WCAG 2.1 AA compliance (4.5:1 contrast, focus indicators, aria-labels) |

**Accessibility Implementation**:
- Focus indicators: 2px outline `#3B82F6` on interactive elements.
- Screen readers: `aria-live="polite"` on message list.
- Keyboard navigation: Tab order managed correctly. Enter submits.

#### 7.6 Privacy & Compliance in the UI
| Requirement | UI Implementation |
|-------------|-------------------|
| No PII collection | No forms, no login, no cookies for tracking |
| No local storage | Chat history lost on refresh (by design) |
| No third-party trackers | No Google Analytics, no Meta Pixel, no CDN cookies |

#### 7.7 Production Build & Deployment
| Input | Development build |
| Output | Optimized production assets |
| Sub-phases | TypeScript compilation → CSS optimization → Asset minification → Docker integration |
| Build Output | Static assets served via Nginx in Docker container |
| Enforcement | Build validation; bundle size optimization; security headers |

#### 7.8 File Structure & Implementation Sample
**File Structure**:
```text
src/
├── components/
│   ├── Header.tsx, DisclaimerBadge.tsx, WelcomeScreen.tsx, etc.
├── hooks/
│   └── useChat.ts, useApi.ts
├── utils/
│   └── constants.ts, sanitizers.ts
├── App.tsx, main.tsx, index.css
```

**Sample Hook (`useChat.ts`)**:
```typescript
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  // ... sends request to /api/query, handles type: answer|refusal|unknown|error
}
```

---

## 5. Complete Data Flow

```
[User opens app]
    ↓
[UI renders WelcomeScreen with 3 example questions]
    ↓
[User types query OR clicks example]
    ↓
[POST /api/query {query: string}]
    ↓
┌─────────────────────────────────────────────────────────────┐
│  API Gateway (FastAPI)                                       │
│  ├── Rate limit check (10 req/min per IP)                   │
│  └── Parse + validate Pydantic schema                        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: Query Sanitization & Classification               │
│  ├── 1.1 PII Detection → [ENFORCEMENT: BLOCK if PII]       │
│  │      └── T1: "I cannot process personal information..."  │
│  ├── 1.2 Intent Classification                              │
│  │      └── ADVISORY? → [ENFORCEMENT: REFUSE]              │
│  │             └── T2: Refusal template + AMFI link         │
│  └── 1.3 Normalization + Entity Resolution                  │
└─────────────────────────────────────────────────────────────┘
    ↓ (if FACTUAL)
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: Corpus Retrieval                                  │
│  ├── 2.1 Query normalization (synonyms, aliases)            │
│  ├── 2.2 Hybrid retrieval (dense + BM25 + structured KV)    │
│  └── 2.3 Relevance filter → [ENFORCEMENT: ≥0.75 threshold] │
│         └── Below threshold? → T3: "I do not have..."       │
└─────────────────────────────────────────────────────────────┘
    ↓ (if results found)
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: Context Assembly                                  │
│  ├── 3.1 Whitelist validation → [ENFORCEMENT: discard bad]  │
│  ├── 3.2 Single source selection → [ENFORCEMENT: P2]       │
│  └── 3.3 Context block assembly                             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Response Generation                               │
│  ├── 4.1 Prompt construction (locked template)              │
│  ├── 4.2 LLM inference (temperature=0.0, max_tokens=150)    │
│  └── 4.3 Failure? → T4: "I'm unable to answer..."          │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: Compliance Validation                             │
│  ├── 5.1 Advisory scan → [ENFORCEMENT: discard if match]   │
│  │      └── T2: Refusal template                             │
│  ├── 5.2 Hallucination scan → [ENFORCEMENT: discard]       │
│  │      └── T3: Unknown template                             │
│  ├── 5.3 Length check → [ENFORCEMENT: ≤3 sentences]        │
│  │      └── Violation? → truncate or T3                     │
│  └── 5.4 Citation injection + footer                        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 6: Response Delivery                                 │
│  └── JSON payload to frontend                                │
└─────────────────────────────────────────────────────────────┘
    ↓
[UI renders AssistantMessage with text, source link, footer]
```

---

## 6. Component Breakdown

### 6.1 Backend Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `main.py` | Entry point | FastAPI app, middleware, CORS |
| `routes/query.py` | API route | `/api/query` endpoint, rate limiting |
| `orchestrator.py` | Core engine | FSM implementation, phase coordination |
| `gates/pii.py` | PII detection | Regex scanner, exemption list |
| `gates/intent.py` | Intent classifier | Rule-based advisory/factual classification |
| `retrieval/hybrid.py` | Retrieval engine | Dense + BM25 + structured KV fusion |
| `retrieval/reranker.py` | Reranker | Cross-encoder + domain-specific boosts |
| `retrieval/entities.py` | Entity resolver | Fund alias mapping, fact synonym mapping |
| `generation/prompts.py` | Prompt templates | Locked system prompt, version hash |
| `generation/llm.py` | LLM client | Groq API inference with deterministic params; OpenAI-compatible SDK |
| `compliance/validator.py` | Validation layer | Advisory scan, hallucination check, length check |
| `compliance/banned.py` | Banned phrases | Version-controlled phrase list |
| `ingestion/fetcher.py` | HTTP fetcher | ETag, retries, anti-bot, circuit breaker |
| `ingestion/extractor.py` | HTML extractor | DOM parsing, structured field extraction |
| `ingestion/chunker.py` | Chunking engine | Semantic splitting, fact-type tagging |
| `ingestion/embedder.py` | Embedding client | BGE model inference |
| `storage/chroma_store.py` | Vector store | Chroma DB client, collection management, metadata filtering |
| `storage/sqlite_store.py` | Structured store | SQLite facts table |
| `observability/logger.py` | Logging | Structured JSON logs, PII-free |
| `observability/metrics.py` | Metrics | Prometheus counters and gauges |

### 6.2 Frontend Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `App.tsx` | Root | State management, screen routing |
| `Header.tsx` | Header | Title + persistent disclaimer badge |
| `WelcomeScreen.tsx` | Welcome | Welcome message + example questions |
| `ChatInterface.tsx` | Chat | Message list + input area |
| `AssistantMessage.tsx` | Message | Render answer/refusal/unknown/error |
| `SourceCitation.tsx` | Citation | Clickable source link |
| `InputArea.tsx` | Input | Text input + send button + validation |

---

## 7. Data Models

```python
# Core schemas (Pydantic)
class QueryRequest(BaseModel):
    query: str = Field(..., max_length=200)

class QueryResponse(BaseModel):
    type: Literal["answer", "refusal", "unknown", "error"]
    text: str
    source_url: str | None
    footer_date: str

class ResolvedQuery(BaseModel):
    original_query: str
    normalized_query: str
    mentioned_funds: list[str]
    fund_resolution_confidence: float
    fact_type: str | None
    fact_confidence: float
    is_ambiguous: bool

class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    source_url: str
    chunk_type: str
    text: str
    embedding: list[float] | None = None

class ComplianceResult(BaseModel):
    status: Literal["APPROVED", "REJECTED"]
    response: str
    violations: list[str]
    fallback_used: str | None
```

---

## 8. Enforcement Points Summary

| ID | Location | Rule | Violation Action |
|----|----------|------|------------------|
| E1 | Ingestion fetch | URL must be in whitelist | Reject fetch, log security event |
| E2 | Ingestion chunk | Every chunk must have `source_url` | Discard chunk |
| E3 | PII Gate | No PAN/Aadhaar/phone/email/account/OTP | T1: Block response |
| E4 | Intent Gate | Advisory score ≥ 0.5 | T2: Refusal template |
| E5 | Retrieval | Similarity must be ≥ 0.75 | T3: Unknown template |
| E6 | Context Assembly | `source_url` must be in whitelist | Discard chunk, fallback to next |
| E7 | Context Assembly | Only one `source_url` per response | Select highest, discard others |
| E8 | LLM Prompt | Temperature must be 0.0 | Enforced in client config |
| E9 | Compliance | No banned phrases in response | Discard, return T2 |
| E10 | Compliance | All numbers must exist in context | Discard, return T3 |
| E11 | Compliance | Max 3 sentences | Truncate or T3 |
| E12 | Citation | Exactly one URL from whitelist | Inject from metadata; never generate |
| E13 | Footer | Every response has `Last updated` | Appended by orchestrator |
| E14 | UI | Disclaimer must be visible | Non-dismissible badge |

---

## 9. Terminal States (Final Responses)

| State | Trigger | Response Body | Source | Footer |
|-------|---------|---------------|--------|--------|
| **T1** | PII detected | "I cannot process personal information. Please ask factual questions about mutual funds." | N/A | Yes |
| **T2** | Advisory intent or advisory language in output | "I can only share factual information from official sources. I cannot provide investment advice or recommendations." + AMFI link | N/A | Yes |
| **T3** | Low confidence, no results, hallucination, length violation | "I do not have that information in my current sources." | N/A | Yes |
| **T4** | System error, timeout, LLM failure | "I'm unable to answer right now. Please try again later." | N/A | Yes |
| **T5** | All checks pass | Factual answer (1-3 sentences) | Whitelist URL | Yes |

---

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Groww blocks scraping** | Medium | High | `curl_cffi` for TLS fingerprinting; randomized delays; single-threaded fetches; if blocked, retain previous corpus and alert |
| **Groww data differs from official AMC factsheet** | Medium | High | Add UI disclaimer: "Data sourced from Groww.in"; periodic manual spot-check against AMC website |
| **LLM hallucinates despite constraints** | Low | Critical | Post-generation hallucination scanner; faithfulness checker; context-only prompt |
| **Advisory query slips through classifier** | Low | Critical | Safe default (unclear → advisory); post-generation advisory scan as backup |
| **PII false positive blocks legitimate query** | Low | Medium | Exemption list for fund names; manual review channel |
| **Embedding model update changes vectors** | Low | High | Version embeddings; re-embed corpus atomically on model change |
| **Vector DB corruption** | Low | High | Daily Chroma snapshot; SQLite as fallback; Chroma persistence enables easy restore |
| **Groq API outage** | Medium | High | Failover chain: secondary Groq model → Gemini API → local Llama-3.1 via Ollama; graceful degradation |
| **Page layout change breaks extraction** | Medium | Medium | Raw text fallback; extraction confidence logging; alert on LOW confidence spike |
| **User prompt injection** | Medium | High | No `dangerouslySetInnerHTML`; input length limit; no system prompt exposure |

---

## 11. Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React SPA     │────▶│  FastAPI Server │────▶│   Chroma DB     │
│   (Vite build)  │     │   (Docker)      │     │   (Persistent)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │   SQLite DB     │
                        │ (structured facts│
                        │  + audit logs)   │
                        └─────────────────┘
                                │
                                ▼
                        ┌───────────────────┐
                        │   LLM Provider    │
                        │ Groq/Gemini/Ollama│
                        └───────────────────┘
```

**Docker Compose**:
```yaml
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - chroma_data:/app/chroma_db
    environment:
      - LLM_PROVIDER=groq
      - GROQ_MODEL=llama3-8b-8192
      - GROQ_API_KEY=${GROQ_API_KEY}
      - GEMINI_MODEL=gemini-1.5-flash
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - TEMPERATURE=0.0
  frontend:
    build: ./phase_7_frontend
    ports:
      - "3000:80"
    depends_on:
      - api
volumes:
  chroma_data:
```

---

## 12. Implementation Checklist

### Week 1: Foundation
- [ ] Set up FastAPI project with Pydantic schemas
- [ ] Implement PII gate and intent classifier
- [ ] Build ingestion fetcher with ETag and retry logic
- [ ] Create chunker with fact-type tagging

### Week 2: Retrieval & Generation
- [ ] Integrate BGE embedding model
- [ ] Build Chroma DB collection + SQLite structured store
- [ ] Implement hybrid retrieval + reranker
- [ ] Build LLM client with locked prompt template

### Week 3: Compliance & UI
- [ ] Implement compliance validator (advisory, hallucination, length, citation)
- [ ] Build React frontend with all screen states
- [ ] Integrate frontend with `/api/query` endpoint
- [ ] Add persistent disclaimer badge

### Week 4: Testing & Observability
- [ ] Build golden dataset (91 fact items, 75 refusal cases)
- [ ] Implement evaluation framework
- [ ] Add structured logging and Prometheus metrics
- [ ] Write README with setup instructions, AMC selection, architecture

### Go-Live Gates
- [ ] Exact Match Rate ≥ 85%
- [ ] Refusal Recall = 100%
- [ ] Hallucination Rate = 0%
- [ ] Citation correctness = 100%
- [ ] PII blocking = 100%
- [ ] All enforcement points tested and passing

---

## 13. Final Compliance Statement

This architecture implements a **defense-in-depth compliance strategy**:

1. **Prevention**: PII gate, intent classifier, locked prompt, context isolation
2. **Detection**: Post-generation advisory scan, hallucination checker, citation validator
3. **Remediation**: Deterministic fallback templates, no in-place sanitization
4. **Audit**: PII-free structured logs, immutable configuration versioning, query/response hashing

Every hard constraint from the Problem Statement is mapped to at least one enforcement point (E1–E14). No single component failure can bypass the compliance layer.

---

## Appendix A: Data Source Override & Compliance Position

The original Problem Statement (Section: Constraints > Data and Sources) mandates:
> "Use only official public sources (AMC, AMFI, SEBI). Do not use third-party blogs or aggregator websites."

The user has explicitly overridden this constraint to use 7 Groww URLs. The architecture formalizes this override via:

- **Immutable whitelist** (Section 8, E1–E2): Only the 7 Groww URLs can enter the system.
- **No runtime addition**: Adding a source requires code change + redeployment.
- **Transparency mitigation**: UI displays "Data sourced from Groww.in" on every response.
- **Audit note**: All logs record `source_url_hash` for traceability.

**Residual Risk**: Groww is an aggregator, not an official AMC source. Data may differ from official factsheets. This is logged as a known limitation.

---

## Appendix B: Evaluation Framework

### B.1 Golden Dataset

| Category | Count | Source |
|----------|-------|--------|
| Fact items (exact match) | 91 | 7 funds × 13 fact types |
| Refusal test cases | 75 | 45 advisory + 20 factual controls + 10 edge cases |
| PII test cases | 40 | 30 PII variants + 10 clean controls |
| Format test cases | 30 | Sentence count, footer, citation |

### B.2 Pass/Fail Thresholds

| Metric | Threshold | Release Blocker |
|--------|-----------|-----------------|
| Exact Match Rate | ≥ 85% | Yes |
| Fuzzy Match Rate | ≥ 95% | Yes |
| Hallucination Rate | 0% | Yes |
| Cross-Fund Error Rate | 0% | Yes |
| Refusal Recall | 100% | Yes |
| False Answer Rate (advisory) | 0% | Yes |
| Citation Presence | 100% | Yes |
| Citation Whitelist Membership | 100% | Yes |
| PII Input Blocking | 100% | Yes |
| PII Output Leakage | 0% | Yes |
| Sentence Compliance (≤3) | 100% | Yes |
| Footer Presence | 100% | Yes |

### B.3 Regression Policy

Any commit causing a previously passing test to fail is automatically reverted.

---

## Appendix C: Observability Specification

### C.1 Structured Log Events

| Event | Fields | Retention |
|-------|--------|-----------|
| `query_received` | `query_hash`, `query_length`, `session_id` | 30 days |
| `intent_classified` | `query_hash`, `classification`, `advisory_score` | 30 days |
| `retrieval_complete` | `query_hash`, `doc_id`, `similarity_score`, `latency_ms` | 30 days |
| `response_generated` | `query_hash`, `response_hash`, `source_doc_id`, `sentence_count` | 30 days |
| `validation_result` | `query_hash`, `response_hash`, `status`, `violations` | 90 days |
| `compliance_violation` | `query_hash`, `response_hash`, `violation_type` | 90 days |
| `ingestion_run` | `run_id`, `urls_processed`, `chunks_created`, `duration_s` | 90 days |

**Privacy rule**: Raw query text and raw response text are NEVER logged. Only SHA-256 hashes.

### C.2 Metrics & Thresholds

| Metric | Target | Critical Alert |
|--------|--------|----------------|
| `factual.accuracy.exact_match_rate` | ≥ 85% | < 80% |
| `factual.accuracy.hallucination_rate` | 0% | > 0% |
| `refusal.rate.overall` | 15–25% | > 50% |
| `refusal.false_negative_rate` | 0% | > 0% |
| `unknown.rate.overall` | ≤ 20% | > 35% |
| `ops.latency.p95` | < 500ms | > 1000ms |
| `ops.errors.rate` | < 0.1% | > 1% |
| `ingestion.staleness_hours` | < 48h | > 48h |

### C.3 Alerts

| Condition | Severity | Channel | Response Time |
|-----------|----------|---------|---------------|
| Compliance violation (any) | P1-Critical | PagerDuty + Slack #alerts-critical | 15 min |
| Ingestion failure (any URL) | P2-High | Slack #alerts-high | 1 hour |
| Corpus hash mismatch | P2-High | Slack #alerts-high | 1 hour |
| High unknown rate (>35%) | P3-Medium | Slack #alerts-medium | 4 hours |
| High refusal rate (>50%) | P3-Medium | Slack #alerts-medium | 4 hours |
| Stale corpus (>48h) | P3-Medium | Slack #alerts-medium | 4 hours |

---

## Appendix D: Production Gap Mitigations

The following items were identified as gaps versus a full production system. They are documented here for future implementation.

| Gap | Priority | Mitigation |
|-----|----------|------------|
| **DPDP Act 2023 compliance** | High | Add user consent banner; designate grievance officer; publish purpose limitation statement |
| **Fallback LLM provider** | High | Tiered failover: (1) Secondary Groq model → (2) Google Gemini (`gemini-1.5-flash`) → (3) Local Ollama (`llama3.1:8b`); automatic failover with 10s timeout per tier |
| **Query result caching** | High | Redis layer for top 20 frequent queries; TTL 1 hour |
| **Rate limiting** | High | Per-IP: 10 req/min; per-session: 30 req/min; 429 response with retry-after |
| **Multi-AZ deployment** | Medium | Deploy API across 2+ availability zones; load balancer health checks |
| **Vector DB backup** | Medium | Daily Chroma snapshot to S3 (`chroma export` or volume backup); automated restore test weekly |
| **Canary deployments** | Medium | 5% → 25% → 100% rollout; auto-rollback on error rate > 1% |
| **Feature flags** | Medium | Toggle retrieval strategies, prompt versions, validation strictness without redeploy |
| **Immutable audit storage** | Medium | Ship audit logs to WORM storage (e.g., AWS S3 Object Lock) in real-time |
| **Encrypted query vault** | Medium | Store raw queries/responses encrypted; dual-auth access for compliance officer only |
| **Hinglish support** | Low | Transliteration mapping or "Please ask in English" response |
| **Fund lifecycle monitoring** | Low | If fund page 404 for 7 days, alert and remove from active corpus |

---

## Appendix E: Banned Phrase Dictionary (Compliance)

| Category | Examples |
|----------|----------|
| Prescriptive | `should invest`, `must buy`, `need to invest`, `consider investing` |
| Comparative | `better than`, `worse than`, `superior to`, `outperform`, `underperform` |
| Evaluative | `good choice`, `safe option`, `risky bet`, `attractive fund`, `ideal for` |
| Predictive | `will grow`, `expected to rise`, `future returns`, `likely to beat` |
| Action-oriented | `buy now`, `sell immediately`, `switch to`, `redeem now`, `accumulate` |
| Recommendation | `I recommend`, `I suggest`, `I advise`, `my recommendation` |
| Performance comparison | `higher returns`, `lower risk`, `better performance`, `compared to` |

**Update process**: PR review + version bump + redeployment. No runtime modification.

---

## Appendix F: Terminal State Response Templates

### T1: PII Blocked
```
I cannot process personal or sensitive information.
Please ask factual questions about mutual fund schemes.

Source: N/A
Last updated from sources: {date}
```

### T2: Advisory Refusal
```
I can only share factual information from official sources.
I cannot provide investment advice or recommendations.

You can learn more about mutual fund basics here:
https://www.amfiindia.com/investor-corner/knowledge-center.html

Source: N/A
Last updated from sources: {date}
```

### T3: Unknown Answer
```
I do not have that information in my current sources.

Source: N/A
Last updated from sources: {date}
```

### T4: System Error
```
I'm unable to answer right now. Please try again later.

Source: N/A
Last updated from sources: {date}
```

### T5: Factual Answer (assembled dynamically)
```
{1-3 sentences of factual text from LLM}

Source: {whitelist_url_injected_by_orchestrator}
Last updated from sources: {date}
```

---

## Appendix G: Confidence Scoring Formula

```
confidence = (
    0.30 * reranker_score +
    0.25 * entity_resolution_confidence +
    0.20 * fact_type_match_score +
    0.15 * fund_match_score +
    0.10 * structured_lookup_bonus
)
```

| Confidence | Action |
|------------|--------|
| ≥ 0.80 | Proceed with answer |
| 0.60 – 0.79 | Proceed with warning log |
| < 0.60 | Return T3 (Unknown) |
