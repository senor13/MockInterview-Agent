Here's the full plan:

The Interview Agent — Build Plan
What it is
A conversational AI interview agent for mid-senior AI/ML engineer roles. Candidate submits their resume and JD, the agent profiles them, conducts a full adaptive interview, evaluates performance, and delivers a structured feedback report.

Core Architecture
Single agent. Prompt-driven. State as context.
No multi-agent orchestration. No state machine in code. The LLM handles the conversation — state is a structured context block passed every turn that keeps the agent oriented.
Tools the agent has access to:

parse_resume(pdf) → extracts raw text from resume
parse_jd(pdf/text) → extracts job description
search_company(name/url) → fetches company context, stack, recent news
send_report(email, report) → delivers final feedback (later)

Everything else — profiling, interviewing, evaluating, report writing — is the LLM reasoning over context.

The Five Parts of the Agent
1. Resume Profiling
Agent's first job before the interview starts. Takes resume text + JD text + company context and produces a structured profile:

Match score (how well candidate fits the role)
Strengths (what they're good at)
Gaps (what's missing for this role)
Seniority estimate
Priority topics to probe in the interview

This profile shapes everything that follows.
2. Interview Orchestration
The core of the product. A single adaptive conversation that moves through three phases:
Technical phase (40%) — ML fundamentals, system design, deployment, LLMs. Questions drawn from resume, JD, and generic AI/ML knowledge.
Business phase (30%) — product sense, tradeoff reasoning, stakeholder communication, impact thinking.
Behavioral phase (20%) — debugging failures, ambiguity, ownership, conflict.
The agent adapts in real time:

Goes deeper when candidate shows depth
Moves on when candidate struggles after one probe
Follows specific threads the candidate opens
Adjusts difficulty based on running signal
Transitions between phases naturally

3. State Management
A structured context block updated after every turn and passed into every LLM call:
json{
  "candidate_profile": {
    "strengths": [],
    "gaps": [],
    "seniority_estimate": "mid",
    "match_score": 72,
    "priority_topics": []
  },
  "interview_state": {
    "current_phase": "technical",
    "current_topic": "ML system design",
    "topics_covered": [],
    "topics_remaining": [],
    "questions_asked": 3,
    "current_difficulty": "medium",
    "depth_on_current_topic": 1
  },
  "candidate_live_signal": {
    "last_answer_quality": "strong",
    "consecutive_strong": 2,
    "consecutive_struggles": 0,
    "confidence_level": "high"
  }
}
Not a state machine. Just the agent's working memory.
4. Evaluation Engine
Runs after the interview ends. Agent reads the full transcript and scores across dimensions:
DimensionWeightTechnical correctness30%Depth20%Communication15%Practicality15%Problem solving10%Confidence/clarity10%
Produces a structured score per phase and an overall verdict.
5. Feedback Report
The artifact the candidate keeps. Structured, specific, actionable:

Overall verdict and match score
Phase-by-phase breakdown
Specific strengths with examples from the interview
Specific gaps with what a better answer would have looked like
Recommended areas to study
Eventually delivered as a PDF


Build Phases
Phase 1 — Make it work

PDF parsing tool
Company search tool
System prompt (the interviewer's brain)
Basic conversation loop
Hardcoded state structure passed every turn
Simple text output at the end

Goal: one full interview, end to end, no polish. Watch it run, find where it breaks.
Phase 2 — Make it smart

Tune the system prompt based on what broke
Improve state tracking — coverage, difficulty adaptation, topic switching
Build the evaluation engine with structured scoring
Build the feedback report with real specificity
Prompt versioning — track what changed and why

Goal: an interview that feels adaptive and feedback that feels genuinely useful.
Phase 3 — Make it reliable

Session persistence — resume a dropped interview
Rate limiting — protect against abuse
Observability — Langfuse for prompt tracing, turn-level logging
Structured output validation — catch malformed responses
Retries for edge cases

Goal: something you can give to strangers and trust it won't break.
Phase 4 — Make it excellent

Feedback loop — candidates rate question relevance and realism
Evaluation pipeline — score consistency checks across sessions
Data flywheel — transcripts feed prompt improvement
PDF report artifact
Voice layer (STT → LLM → TTS)
Web UI for public access

Goal: a product that gets better the more it's used.