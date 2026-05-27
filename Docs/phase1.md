# Phase 1 — Build Log

## What We Built

A working end-to-end interview agent that:
1. Parses a resume PDF and reads a JD text file
2. Runs a profile extraction agent to produce a structured candidate profile + company info
3. Loads a versioned system prompt and runs a conversation loop
4. Detects interview end via `INTERVIEW_COMPLETE` signal or turn limit
5. Returns the full conversation history (evaluator is next)

---

## Files Created

```
Interview-Agent/
├── main.py                        # Entry point
├── config.py                      # Constants and env vars
├── sample_jd.txt                  # Test JD input
├── agent/
│   ├── __init__.py
│   ├── llm.py                     # call_llm helper (OpenAI + Instructor)
│   ├── profile_agent.py           # Profile extraction agent
│   └── interviewer.py             # Conversation loop
├── tools/
│   ├── __init__.py
│   ├── parse_pdf.py               # PDF text extraction
│   └── search_company.py          # Tavily company search
├── state/
│   ├── __init__.py
│   └── schema.py                  # Pydantic state models
└── prompts/
    ├── system_v0.1.0.md           # Versioned system prompt
    └── CHANGELOG.md               # Prompt change log
```

---

## What the Agent Does — Flow

```
main.py
  → parse_pdf(resume_path)              # extract resume text
  → read sample_jd.txt                  # read JD text
  → profile_extraction_agent(resume, jd)
        → LLM call with Instructor      # returns CandidateProfile
        → tool call: search_company     # returns company_info
  → interview_agent(resume, jd, company_info, profile)
        → load system prompt from .md
        → init InterviewState + SessionMeta
        → while turns <= 15 and not interview_complete:
              → build messages (system prompt + state + history)
              → call LLM
              → print question
              → get candidate input
              → update state
              → check for INTERVIEW_COMPLETE
  → return conversation_history
```

---

## Code Syntax & Patterns Learned

### 1. Pydantic BaseModel

Define data schemas as typed Python classes. Validates types automatically.

```python
from pydantic import BaseModel
from typing import Literal, List
from datetime import datetime

class InterviewState(BaseModel):
    no_of_turns: int = 0
    topics_covered: List[str] = []
    current_topic: str | None = None
```

### 2. Literal — Fixed Value Sets

Use `Literal` when a field can only be one of a specific set of values.

```python
from typing import Literal

seniority_estimate: Literal["senior", "mid", "junior"]
last_answer_quality: Literal["poor", "strong"] | None = None
```

### 3. Optional Fields

Mark a field as optional with `| None = None`. The field exists but defaults to `None`.

```python
current_topic: str | None = None
ended_at: datetime | None = None
```

### 4. Nested Pydantic Models

Define each section as its own class, then combine in a parent class.

```python
class ResumeProfile(BaseModel):
    match_score: float
    strengths_for_role: List[str]

class StateSchema(BaseModel):
    resume_profile: ResumeProfile      # nested model as a field type
    interview_state: InterviewState
```

### 5. Serialization — model_dump and model_dump_json

Convert a Pydantic object to a dict or JSON string.

```python
state.model_dump()          # → Python dict
state.model_dump_json()     # → JSON string (for injecting into prompts)
```

### 6. Immutable Updates — model_copy

Never mutate a Pydantic object directly. Create a new copy with updated fields.

```python
# WRONG — mutates in place
interview_state.no_of_turns = 5

# CORRECT — returns new object, reassign variable
interview_state = interview_state.model_copy(update={"no_of_turns": 5})
```

### 7. Instructor — Structured LLM Output

Instructor wraps the OpenAI client and forces the LLM to return a typed Pydantic object.

```python
import instructor
from openai import OpenAI

client = OpenAI()
instructor_client = instructor.from_openai(client)

profile = instructor_client.chat.completions.create(
    model="gpt-4o",
    response_model=CandidateProfile,   # LLM must return this shape
    messages=[...]
)

profile.match_score        # directly accessible as typed fields
profile.strengths_for_role
```

### 8. OpenAI Tool Calling Format

Tools are defined as JSON schemas. The LLM decides when to call them.

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "company_search",
            "description": "Fetch details about a company",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "Name of the company"
                    }
                },
                "required": ["company_name"]
            }
        }
    }
]
```

### 9. Tool Call Handling Loop

Always handle tool calls in a loop — the LLM might make multiple calls before responding.

```python
while True:
    response = call_llm(messages=messages, tools=tools)
    if response.tool_calls:
        tool_name = response.tool_calls[0].function.name
        arguments = json.loads(response.tool_calls[0].function.arguments)  # parse JSON string
        tool_result = function_map[tool_name](**arguments)
        messages.append({"role": "assistant", "content": None, "tool_calls": [response.tool_calls[0]]})
        messages.append({"role": "tool", "content": tool_result, "tool_call_id": response.tool_calls[0].id})
    else:
        break
```

### 10. OpenAI Message Format

Messages are a list of dicts with `role` and `content`.

```python
messages = [
    {"role": "system", "content": system_prompt},   # instructions
    {"role": "assistant", "content": "question..."},  # LLM turn
    {"role": "user", "content": "answer..."},         # candidate turn
]
```

### 11. Prompt Templates — .format()

Keep prompts in `.md` files with `{placeholders}`. Fill them in at runtime.

```python
with open("prompts/system_v0.1.0.md", "r") as f:
    template = f.read()

system_prompt = template.format(
    resume_text=resume_text,
    jd_text=jd_text,
    candidate_profile=candidate_profile.model_dump_json()
)
```

### 12. Two-Client Pattern (OpenAI + Instructor)

Use the regular client for normal calls, Instructor client for structured output.

```python
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
instructor_client = instructor.from_openai(client)

def call_llm(messages, tools=None, response_model=None):
    kwargs = {"model": INTERVIEWER_MODEL, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    if response_model:
        kwargs["response_model"] = response_model
        return instructor_client.chat.completions.create(**kwargs)
    else:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message
```

### 13. Error Handling at System Boundaries

Validate inputs at the function boundary. Use specific exception types.

```python
def parse_pdf(path: str) -> str:
    if not path:
        raise ValueError("Path cannot be empty or None")
    if not os.path.exists(path):
        raise FileNotFoundError(f"PDF file not found at path: {path}")
```

### 14. Package Structure — __init__.py

Every folder that contains Python modules needs an empty `__init__.py` to be importable as a package.

```bash
touch tools/__init__.py
touch state/__init__.py
touch agent/__init__.py
```

Then import using the full module path:
```python
from tools.parse_pdf import parse_pdf
from state.schema import CandidateProfile
from agent.llm import call_llm
```

### 15. UUID and Timestamps

Generate unique session IDs and ISO format timestamps.

```python
import uuid
from datetime import datetime

session_id = str(uuid.uuid4())                  # "a1b2c3d4-..."
started_at = datetime.now().isoformat()          # "2026-05-27T10:30:00"
```

---

## Key Decisions Made in Phase 1

| Decision | Choice | Reason |
|---|---|---|
| State update mechanism | Hybrid — code for counters, LLM for signals | Least hallucination surface |
| Question distribution | Instruction-only, no real-time enforcement | Don't constrain before seeing data |
| Context window | Full transcript for now | Phase 1 interviews short enough |
| Memory | Agent always fresh — no cross-session context | Fair evaluation, unbiased |
| PDF parsing | pdfplumber | Better multi-column resume handling |
| Company search | Tavily API | Purpose-built for LLM agents |
| Structured output | Instructor + Pydantic | No manual JSON parsing |
| Prompt storage | Versioned .md files | Independent from code changes |

---

## What's Next — Phase 2

- [ ] Build `agent/evaluator.py` — post-interview scoring and feedback report
- [ ] Add Langfuse observability to all LLM calls
- [ ] Add LLM extraction call for `CandidateLiveSignal`
- [ ] Tune system prompt based on Phase 1 interview runs
- [ ] Add summarization tool (trigger-based on token threshold)
- [ ] Structured output validation and retry logic
