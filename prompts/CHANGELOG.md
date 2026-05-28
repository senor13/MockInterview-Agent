## v0.1.0 — 2026-05-25
Initial system prompt. Basic interviewer instructions, resume/JD/profile/state placeholders.

- It moved to wrap-up after only 9-10 turns — well under the 15 turn limit. The LLM is ending early.
- Questions are decent but somewhat generic — "tell me about Python libraries" could be more specific given the resume
- Unnecessary wording in beginning of each question and not deep diving properly.
- Scoring criteria not set

## v0.1.1 — 2026-05-28
  **Change:** Added instruction to avoid markdown formatting in responses.
  **Why:** LLM was using headers and bold text in interview responses, making it feel unnatural.
  **Impact:** To be observed in next test run.