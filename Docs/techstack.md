# Tech Stack

---

## LLM Provider — Anthropic (Claude)

| Task | Model | Reason |
|---|---|---|
| Main interviewer | `claude-sonnet-4-6` | Best reasoning, handles long adaptive conversations |
| Resume profiling | `claude-sonnet-4-6` | Needs nuance to produce a quality profile |
| Evaluation analyst | `claude-sonnet-4-6` | Multiple judgment calls across dimensions |
| State extraction (Phase 2) | `claude-haiku-4-5` | Cheap, fast, narrow focused task |
| Summarization tool | `claude-haiku-4-5` | Focused transformation — no deep reasoning needed |

---

## Core Libraries

| Library | Purpose |
|---|---|
| `anthropic` | Official Anthropic SDK |
| `instructor` | Structured Pydantic output from LLM calls — wraps the Anthropic SDK |
| `pydantic` | Data models, schema validation for state block, profile, evaluation output |
| `pdfplumber` | PDF parsing — handles multi-column resumes and tables reliably |

**Why Instructor:**
Gets typed, validated Pydantic objects from LLM calls cleanly. Used for resume profiling output, state extraction call (Phase 2), and evaluation output.

```python
import instructor
from anthropic import Anthropic
from pydantic import BaseModel

client = instructor.from_anthropic(Anthropic())

class CandidateProfile(BaseModel):
    match_score: int
    strengths: list[str]
    gaps: list[str]
    seniority_estimate: str
    priority_topics: list[str]

profile = client.chat.completions.create(
    model="claude-sonnet-4-6",
    response_model=CandidateProfile,
    messages=[...]
)
```

---

## Tools

| Tool | Library / API | Phase |
|---|---|---|
| `parse_resume` | `pdfplumber` | Phase 1 |
| `parse_jd` | `pdfplumber` + plain text | Phase 1 |
| `search_company` | Tavily API | Phase 1 |
| `summarize_conversation` | Anthropic SDK (Haiku) | Phase 2 |
| `send_report` | Email API (TBD) | Phase 4 |

**Tavily:** Purpose-built for LLM agents. Returns clean summarized results, not raw HTML. Free tier sufficient for Phase 1.

---

## Database

| Phase | DB | Hosting |
|---|---|---|
| Phase 1–2 | SQLite | Local file |
| Phase 3+ | PostgreSQL | Supabase (managed) |

Schema designed to PostgreSQL conventions from Phase 1 — migration is a connection string swap, not a rewrite.

```sql
candidates:  id, email, name, created_at
sessions:    id, candidate_id, role, jd_text, prompt_version, started_at, completed_at, status
turns:       id, session_id, turn_number, role, content, timestamp
evaluations: id, session_id, scores (json), distribution (json), report_text, created_at
```

---

## Observability

**Langfuse** — wired in from Phase 1.

Tags on every trace:
- `session_id`
- `prompt_version`
- `turn_count`

Additional tags added per phase:
- Phase 2: `answer_quality`, `current_difficulty`
- Phase 4: `evaluation_score`

---

## API Layer

**FastAPI** (Phase 3) — standard, fast, Pydantic models double as request/response schemas.

---

## UI

| Phase | Tool | Reason |
|---|---|---|
| Phase 3 | Streamlit | Fast to build, good for testing with real users |
| Phase 4 | Next.js | Production UI — candidate dashboard, history, progress tracking |

---

## Report Generation

| Phase | Format | Tool |
|---|---|---|
| Phase 1 | Markdown (terminal) | — |
| Phase 3 | Structured JSON + formatted text | — |
| Phase 4 | PDF | `weasyprint` (HTML → PDF) |

---

## Voice Layer (Phase 4 — Exploratory)

Evaluate when Phase 4 is reached. Do not build infrastructure for this earlier.

| Component | Options to evaluate |
|---|---|
| STT (speech to text) | OpenAI Whisper, Deepgram |
| TTS (text to speech) | ElevenLabs, OpenAI TTS |

---

## No Agent Framework

No LangGraph, no LangChain. The architecture is a single conversation loop — assembling context, calling LLM, updating state. A framework adds a state machine on top of something that doesn't need one. Raw Anthropic SDK keeps it explicit and debuggable.

---

## Summary

```
Core:          Python, Anthropic SDK, Instructor, Pydantic
Parsing:       pdfplumber
Search:        Tavily API
DB:            SQLite → PostgreSQL (Supabase)
Observability: Langfuse
API:           FastAPI (Phase 3)
UI:            Streamlit (Phase 3) → Next.js (Phase 4)
Report:        Markdown → PDF via weasyprint (Phase 4)
Voice:         Whisper + ElevenLabs (Phase 4, exploratory)
```
