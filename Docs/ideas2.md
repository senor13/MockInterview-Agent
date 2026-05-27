# The Interview Agent — Full Plan (v2)

> Tech stack decisions live in [techstack.md](./techstack.md)

---

## What It Is

A conversational AI interview agent for mid-senior AI/ML engineer roles. Candidate submits their resume and JD, the agent profiles them, conducts a full adaptive interview, evaluates performance, and delivers a structured feedback report.

---

## Explicit Design Decisions

These are the load-bearing decisions that must be made before writing the first line of code. Each one has options — pick one and commit. You can revisit in Phase 2 based on what breaks.

---

### Decision 1: State Update Mechanism

After every turn, the state block needs to change. Three options:

**Option A — Single LLM call (LLM updates state + generates response)**
LLM returns a structured JSON response containing both the interviewer's message and updated state fields.
- Pro: One API call, lowest latency
- Con: LLM will hallucinate state values (e.g., `questions_asked: 3` when it's 6). Hard to catch.
- Verdict: Fragile for v1.

**Option B — Two LLM calls (response + extraction)**
Call 1: LLM generates the interviewer's next question.
Call 2: A cheaper, focused call extracts state updates from the exchange.
- Pro: Cleaner separation, state extraction is focused and easy to validate
- Con: 2x latency and cost per turn
- Verdict: Good for Phase 2 when you care about quality over speed.

**Option C — Hybrid ✅ DECIDED**
Code handles deterministic fields (counters, lists). LLM only updates qualitative signals.

```
Code updates:    questions_asked, topics_covered, current_phase
LLM updates:     last_answer_quality, current_difficulty, confidence_level
```

- Pro: Least hallucination surface, easiest to debug
- Con: Slightly more logic in code

---

### Decision 2: Question Flow & Distribution ✅ DECIDED

**No phases. No sequential structure. No script.**

The LLM picks questions freely, drawing from the candidate's resume, the JD, and its own domain knowledge. It decides what to ask next based on what would be most revealing — not a pre-planned script.

**Distribution target (instruction only — not enforced in Phase 1):**
| Question type | Target |
|---|---|
| Technical | 50% |
| Business | 30% |
| Behavioral | 20% |

The LLM is instructed to approximate this distribution but is not monitored or corrected in real-time. No per-turn categorization. No running distribution in state. The LLM interviews freely — these are guidelines, not guardrails.

**Why no real-time enforcement initially:**
Don't constrain before you have data. The evaluation captures actual distribution after every session. If results consistently show bad drift, add a running distribution + per-turn categorization call in Phase 2. If the LLM approximates well by instruction alone, the mechanism never needs to be built. The evaluation is the decision gate.

**Follow-up depth rule (hard, code-enforced):**
After a main question, the LLM may ask at most 2 follow-up questions on the same topic.
- `depth = 0` → main question
- `depth = 1` → first follow-up (go deeper if answer showed strength)
- `depth = 2` → second follow-up (maximum — code forces topic change after this)

Code tracks `current_topic_depth`. When it hits 2, the next turn's context includes an explicit instruction to move to a new topic. The LLM still chooses what topic and question — code only enforces the ceiling.

**What gets tracked in state (Phase 1):**
```json
"interview_state": {
  "current_topic": "LLM deployment",
  "current_topic_depth": 1,
  "max_follow_up_depth": 2,
  "topics_covered": ["ML system design", "LLM deployment"],
  "topics_remaining": ["experimentation platforms"],
  "total_turns": 11
}
```

Lean. No type counts, no distribution math during the interview. That all happens at the end.

**Why no script:**
Scripts lock the interview into a fixed question set. The whole point is adaptive questioning — a candidate who mentions Kubernetes in their resume should get probed on Kubernetes, not a generic "describe your deployment experience." The resume + JD + LLM knowledge is the question bank.

**Evaluation captures (post-interview — analyst LLM call on full transcript):**
- Actual question distribution vs. 50/30/20 target
- Question quality — specific to this candidate, or generic?
- Prompt consistency — did the LLM follow its own stated rules?
- Follow-up depth — was the max-2 rule respected?

**Phase 2 decision gate:**
Only add running distribution + per-turn categorization if ALL of the following are true:
- Distribution drift is consistently > 15% off target across 5+ sessions
- AND evaluation scores suggest the imbalance is hurting interview quality
- AND candidate feedback signals the interview felt lopsided or incomplete

If evaluation quality is good and candidates rate the interview well, distribution drift is irrelevant — the 50/30/20 target was always a proxy for quality, not the goal itself. Don't add the mechanism just because the numbers are off.

---

### Decision 3: Context Window Strategy ✅ DECIDED

**Trigger-based summarization.**

Phase 1: pass the full transcript every turn. Simple, no risk of losing context.

When transcript exceeds a token threshold (e.g., ~3,000–4,000 tokens of conversation history), trigger a summarization call. From that point: pass summary + last 3–4 turns verbatim. The summary is updated each time the threshold is crossed again.

**Implemented as a tool, not a sub-agent.** `summarize_conversation(transcript) → str`. The threshold check is in orchestration code — the LLM doesn't decide when to summarize, code does. Summarization is a focused transformation, not a reasoning task.

```
Transcript length < threshold  →  pass full transcript
Transcript length ≥ threshold  →  summarization call → pass summary + last N turns
```

The summarization call is a separate, focused LLM call — not the main interviewer. It compresses what's been covered, what signals emerged, and what topics remain. This also feeds naturally into the evaluation at the end.

Use Langfuse to track token usage per session from Phase 1. The data tells you where the threshold should actually sit.

---

### Decision 4: Memory Architecture ✅ DECIDED

Three layers, each with a clear purpose:

**Layer 1 — Session state (ephemeral, in-memory)**
The state block. Lives only for the duration of the interview. Already covered.

**Layer 2 — Session persistence (Phase 3)**
Serialize the full session (state block + transcript) to DB at the end of each turn. Allows resuming a dropped interview. Candidate identity required (email or ID) to retrieve their session.

**Layer 3 — Candidate history (Phase 4)**
All past sessions stored and queryable per candidate. Score progression, topics covered, improvement over time. Surfaced in two ways:
- Candidate dashboard — full history across sessions
- Progress section in the feedback report — delta vs. previous session, what improved, what still needs work

**The key rule: the agent always starts fresh.**
Previous sessions are never fed into the interviewer's context — regardless of whether it's the same role or a different one. The agent evaluates the candidate as they present today, not as they performed before. Past performance stays in the DB, visible to the candidate, invisible to the agent.

This keeps evaluation fair and unbiased across sessions.

**Data model implication (design now, don't repaint later):**
```
candidates:  id, email, name, created_at
sessions:    id, candidate_id, role, jd_text, prompt_version, started_at, completed_at, status
turns:       id, session_id, turn_number, role, content, timestamp
evaluations: id, session_id, scores (json), distribution (json), report_text, created_at
```

Candidate history is just querying `sessions + evaluations` by `candidate_id`. No special architecture needed — the schema handles it.

---

## Core Architecture

Single agent. Prompt-driven. State as context. No multi-agent orchestration. No framework-level state machine.

The LLM handles conversation logic. Code handles bookkeeping. State block is the handshake between them.

```
[User message]
      ↓
[Assemble context: system prompt + state block + transcript window]
      ↓
[LLM call → interviewer response]
      ↓
[Code updates deterministic state fields]
      ↓
[LLM extraction call → qualitative state fields]  ← add in Phase 2
      ↓
[Persist updated state]
      ↓
[Return response to user]
```

**Tools the agent has access to:**
- `parse_resume(pdf_path) → str` — extracts raw text from PDF
- `parse_jd(pdf_path | text) → str` — extracts job description
- `search_company(name | url) → str` — fetches company context, stack, recent news
- `send_report(email, report) → void` — delivers final feedback (Phase 4)

Everything else — profiling, interviewing, evaluating, report writing — is LLM reasoning over context.

---

## The Five Parts

### 1. Resume Profiling

Runs once before the interview starts. Not a conversation — a structured analysis call.

Input: resume text + JD text + company context
Output (structured JSON):
```json
{
  "match_score": 72,
  "strengths": ["strong MLOps background", "production LLM experience"],
  "gaps": ["no experience with real-time inference at scale"],
  "seniority_estimate": "mid-senior",
  "priority_topics": ["ML system design", "LLM deployment", "experimentation platforms"]
}
```

The profile JSON and the full resume + JD text are both injected into the system prompt at session start. The system prompt is assembled once and stays fixed for the entire interview.

```
System prompt =
  interviewer instructions + rules
  + full resume text          ← raw, complete
  + full JD text              ← raw, complete
  + candidate profile JSON    ← structured quick-reference: what to prioritize
```

The profile JSON is a pre-computed "here's what matters most" layer on top of the raw text — not a replacement for it. The LLM reads the actual resume to ask specific, grounded questions ("you built a feature store at 10M events/sec — walk me through the consistency guarantees"), not generic ones derived from a compressed summary.

Neither changes during the interview.

---

### 2. Interview Orchestration

A single adaptive conversation. No fixed phases. No scripts.

The LLM picks questions freely, drawing from resume + JD + domain knowledge, targeting this distribution across the full interview:

| Question type | Target | Focus |
|---|---|---|
| Technical | 50% | ML fundamentals, system design, deployment, LLMs |
| Business | 30% | Product sense, tradeoff reasoning, stakeholder communication |
| Behavioral | 20% | Debugging failures, ambiguity, ownership, conflict |

Plus a short wrap-up (candidate questions, closing) — not counted in the distribution.

Adaptation rules (encoded in system prompt):
- Ask questions grounded in this specific candidate's resume and JD, not generic templates
- Go deeper when candidate shows depth — max 2 follow-up questions per topic (code enforces)
- Move on after max follow-ups or when candidate is clearly stuck
- Follow specific threads the candidate opens
- Adjust difficulty based on running signal in state block
- Approximate the 50/30/20 distribution by instruction — no real-time tracking in Phase 1. Actual distribution is captured at end of interview by the evaluation analyst.

---

### 3. State Management

Updated after every turn. Passed into every LLM call. The agent's working memory.

```json
{
  "candidate_profile": {
    "strengths": [],
    "gaps": [],
    "seniority_estimate": "mid",
    "match_score": 72,
    "priority_topics": []
  },
  "interview_state": {
    "current_topic": "LLM deployment",
    "current_topic_depth": 1,
    "max_follow_up_depth": 2,
    "topics_covered": ["ML system design", "LLM deployment"],
    "topics_remaining": ["experimentation platforms"],
    "total_turns": 11
  },
  "candidate_live_signal": {
    "last_answer_quality": "strong",
    "consecutive_strong": 2,
    "consecutive_struggles": 0,
    "overall_signal": "tracking_above_target"
  },
  "session_meta": {
    "session_id": "uuid",
    "prompt_version": "v0.1.0",
    "started_at": "2026-05-22T10:00:00Z"
  }
}
```

No question type counts, no running distribution. Those are computed at the end of the interview by the evaluation analyst from the full transcript — not tracked turn-by-turn.

**Who updates what:**

| Field | Updated by | When |
|---|---|---|
| `current_topic_depth` | Code | Increments on follow-up, resets when topic changes |
| `topics_covered`, `topics_remaining` | Code | Updated when LLM moves to a new topic |
| `total_turns` | Code | Increments every turn |
| `last_answer_quality`, `overall_signal`, `consecutive_*` | LLM extraction call | Phase 2 — defaults to neutral in Phase 1 |
| `candidate_profile` | Set once at session start | Never changes during the interview |
| `session_meta` | Set once at session start | Never changes |

---

### 4. Evaluation Engine

Runs once after the interview ends. Reads the full transcript + state history and scores across dimensions.

| Dimension | Weight |
|---|---|
| Technical correctness | 30% |
| Depth | 20% |
| Communication clarity | 15% |
| Practicality / applied thinking | 15% |
| Problem solving | 10% |
| Confidence / self-awareness | 10% |

Output: structured score per dimension + overall verdict + specific evidence quotes from transcript.

**Evaluation also captures — every session:**

| Metric | What it tells you |
|---|---|
| Actual question distribution vs. 50/30/20 target | Did the LLM approximate the right balance? |
| Follow-up depth per topic | Did the LLM respect the max-2 rule? |
| Question specificity | Were questions grounded in this resume/JD, or generic? |
| Prompt consistency score | Did the LLM follow its own stated instructions? |

The last one — prompt consistency — is evaluated by a separate judge call that reads the transcript and the system prompt side by side and flags any rules that were visibly violated. This becomes the signal for prompt iteration.

**Evaluation reliability concern (name it now, solve in Phase 4):**
LLM-as-judge is non-deterministic. Same transcript can score differently on different runs. Consistency check: run evaluation 3 times, flag sessions where variance is high. Add in Phase 4.

**Evaluation depth is deliberately deferred.**
The eval pipeline will grow over time — hallucination detection, scoring consistency, prompt consistency checks, question quality signals, and more. These will be designed properly when we reach the evaluation phase. Don't front-load it.

---

### 5. Feedback Report

The artifact the candidate keeps. Structured and specific.

**Sections (every session):**
- Overall verdict and match score
- Score breakdown across evaluation dimensions
- Top 3 strengths with direct quotes from the interview
- Top 3 gaps with "what a stronger answer would have looked like"
- Recommended areas to study (personalized, not generic)

**Progress comparison (Phase 4 — when candidate has prior sessions):**
- Score delta per dimension vs. previous session ("Technical correctness: 62 → 74, +12")
- What improved with specific evidence ("Your system design answers were notably more structured")
- What still needs work vs. last time
- Overall trend across all sessions (if 3+)

This section is only generated if a previous session exists for the same candidate. First-time candidates get the standard report. The comparison pulls from `evaluations` in the DB — no previous transcript is passed to the agent.

**Delivery by phase:**
- Phase 1: Markdown printed to terminal
- Phase 3: Structured JSON + formatted text
- Phase 4: PDF artifact + email delivery + candidate dashboard showing full history

---

## Infrastructure (Start From Day 1)

### Prompt Versioning

Every system prompt lives in `prompts/` with a version tag:

```
prompts/
  system_prompt_v0.1.0.md
  system_prompt_v0.2.0.md
  CHANGELOG.md              ← what changed, why, what impact
```

Every session logs `prompt_version` in its state meta. This lets you correlate prompt changes with evaluation score changes in Phase 4. You cannot retrofit this — start it in Phase 1.

Versioning convention: `MAJOR.MINOR.PATCH`
- PATCH: wording tweaks, tone adjustments
- MINOR: structural changes (new phase instructions, new scoring guidance)
- MAJOR: fundamental redesign of the interviewer's behavior

### Observability (Langfuse from Phase 1)

Tag every trace with:
- `session_id`
- `prompt_version`
- `interview_phase`
- `question_number`
- `turn_count`

This is the foundation for everything in Phase 4. You already know Langfuse — wire it in before you run the first real interview.

In Phase 2: add `answer_quality` and `difficulty` to traces.
In Phase 4: add `evaluation_score` to traces so you can correlate prompt versions → quality signals → final scores.

### Evaluation Pipeline (Phase 4, but design the schema now)

The evaluation loop that makes the agent get better over time:

```
Interview session
      ↓
Langfuse trace (prompt version, turn signals)
      ↓
Post-interview evaluation (LLM-as-judge, scored dimensions)
      ↓
Consistency check (3-run variance flag)
      ↓
Human spot-check on flagged sessions       ← manual in early phases
      ↓
Findings fed into prompt CHANGELOG
      ↓
New prompt version
```

This is the data flywheel. It's only meaningful when you have enough sessions to see patterns (Phase 4). But the schema — session_id, prompt_version, evaluation scores — must be captured from Phase 1.

---

## Build Phases

### Phase 1 — Make It Work

Goal: one full interview, end to end. No polish. Watch it run, find where it breaks.

- [ ] PDF parsing tool (`parse_resume`, `parse_jd`)
- [ ] Company search tool (`search_company`)
- [ ] System prompt v0.1.0 — the interviewer's brain
- [ ] State block structure (Decision 1: **Hybrid** — code handles counters/phase transitions, LLM handles qualitative signals)
- [ ] Phase transition (Decision 2: Option B — rule-based count gates)
- [ ] Basic conversation loop (terminal input/output)
- [ ] State serialized and passed every turn
- [ ] Langfuse wired in from the first call (tag: session_id, prompt_version, phase)
- [ ] `prompts/` directory + `CHANGELOG.md` created
- [ ] Simple markdown feedback report printed at end

**Definition of done:** Run one complete interview with a real resume and JD. Read the transcript. Identify at least 5 specific failures.

---

### Phase 2 — Make It Smart

Goal: an interview that feels adaptive and feedback that feels genuinely useful.

- [ ] Tune system prompt based on Phase 1 failures — log in CHANGELOG
- [ ] Move to Option C phase transitions (soft targets + guardrails)
- [ ] Add LLM extraction call for qualitative state updates
- [ ] Improve topic coverage tracking — ensure all priority topics are hit
- [ ] Difficulty adaptation — verified in Langfuse traces
- [ ] Evaluation engine with structured scoring (6 dimensions + weights)
- [ ] Feedback report with specific quotes and "better answer" examples
- [ ] Context window monitoring — measure token usage per session, decide if rolling summary is needed
- [ ] Structured output validation — catch and retry malformed LLM responses

**Definition of done:** Show the transcript and feedback report to someone outside the project. Would they find the interview realistic? Would they find the feedback useful?

---

### Phase 3 — Make It Reliable

Goal: something you can give to strangers without it breaking.

- [ ] Session persistence — serialize state to disk (SQLite or JSON files), allow resume
- [ ] Retry logic — handle LLM timeouts, malformed outputs, tool failures
- [ ] Rate limiting — protect against abuse (per session, per day)
- [ ] Input validation — sanitize all user inputs before passing to tools or LLM
- [ ] Full Langfuse tracing — every turn, every tool call, every state update logged
- [ ] Structured output schemas — validate state block and evaluation output against schema
- [ ] Error messages — user-facing messages that don't leak internals
- [ ] FastAPI wrapper — expose the agent as an API endpoint

**Definition of done:** Run 10 sessions with different resumes and JDs. Zero crashes. All sessions produce a complete feedback report.

---

### Phase 4 — Make It Excellent

Goal: a product that gets better the more it's used.

- [ ] Candidate feedback loop — rate question relevance and realism per session
- [ ] Evaluation consistency check — run each evaluation 3x, flag high-variance sessions
- [ ] Human spot-check workflow — review flagged sessions, log findings to CHANGELOG
- [ ] Candidate history — track improvement across multiple sessions (requires identity model)
- [ ] Aggregate patterns — anonymized insights across sessions (question bank improvement)
- [ ] PDF report artifact
- [ ] Email delivery (`send_report`)
- [ ] Voice layer — STT → LLM → TTS (exploratory; evaluate Whisper + ElevenLabs vs. full voice APIs)
- [ ] Web UI for public access

**Definition of done:** Run 50+ sessions. Show that evaluation scores are correlated with prompt versions. Show at least one measurable improvement from the feedback loop.

---

### Phase 5 — Scale & Learn (Post-Public Launch)

Goal: let usage volume drive model-level improvement.

Triggered by: significant public usage (hundreds to thousands of sessions with human feedback).

- [ ] Prompt optimization using accumulated feedback as reward signal — treat prompt iteration as the RLHF loop (human ratings → which prompt version performed better → iterate)
- [ ] Few-shot curation — highest-rated sessions become examples injected into the system prompt, improving quality through in-context learning
- [ ] Fine-tuning on open-source model (Llama 3, Mistral, or equivalent) — once volume justifies it. Bakes the interviewer persona and question style into model weights. Enables cost reduction at scale and full ownership of the model.
- [ ] Reward model trained on human ratings — automates quality scoring without LLM-as-judge, validates evaluation pipeline

**Why not earlier:** Fine-tuning requires thousands of rated sessions to be statistically meaningful. Building the infrastructure before the data exists is premature. The prompt optimization loop in Phase 4 is the right path until public scale is reached.

---

## Open Explorations

These are not blockers. They are deliberate experiments to run during the build:

| Question | When to explore | How |
|---|---|---|
| Does a single system prompt scale to all three phases, or does phase-switching benefit from separate prompts? | Phase 2 | A/B in Langfuse — version with one prompt vs. three injected phase-specific blocks |
| How much does company context (`search_company`) actually improve question relevance? | Phase 2 | Compare sessions with and without it — human-rated |
| Is LLM-as-judge reliable enough, or do we need a rubric-grounded model? | Phase 4 | Run 20 sessions, human-rate them, compare to LLM scores |
| Does voice change the quality of answers? | Phase 4 | Run matched pairs (text vs. voice) with the same questions |
| What's the right model? Claude Sonnet for interviewing, Haiku for state extraction? | Phase 2 | Cost/quality tradeoff — measure in Langfuse |

---

## What Good Looks Like at the End

A production-ready agent with:
- A documented prompt evolution history you can walk through
- Langfuse dashboards showing quality trends across sessions
- An evaluation pipeline that gives you signal on what's working
- A feedback report a candidate would genuinely use to prepare
- A clear architectural rationale — why single-agent, why these tools, why this state design — that you can defend in an interview
