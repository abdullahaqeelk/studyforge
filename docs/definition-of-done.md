\# Definition of Done (DOD)



\*\*Project:\*\* StudyForge — Agentic Exam-Preparation System

\*\*Applies to:\*\* All four sprints

\*\*Agreed by:\*\* Abdullah Aqeel Khan, Mubeen Malik, Usman Irshad, M. Husnain



A user story is \*\*Done\*\* only when every item below is satisfied. Partially

complete stories return to the backlog and are re-estimated — they are never

counted toward sprint velocity.



\---



\## 1. Code



\- \[ ] Code implements every acceptance criterion listed on the Jira story

\- \[ ] Code runs without errors on a clean clone of the repository

\- \[ ] No hardcoded API keys, credentials, or absolute local paths

\- \[ ] Functions carry docstrings describing purpose, parameters, and returns

\- \[ ] No commented-out dead code or leftover debug prints



\## 2. Version Control



\- \[ ] Work done on a feature branch named `feature/SF-<id>-<short-description>`

\- \[ ] Every commit message begins with the Jira issue ID (e.g. `SF-12 Add PDF parser`)

\- \[ ] Pull request raised against `main` and reviewed by at least one other member

\- \[ ] Branch merged to `main` and deleted after merge

\- \[ ] `main` remains in a runnable state after the merge



\## 3. AI / Agent-Specific



\- \[ ] Any prompt used is stored as a versioned file under `prompts/`, not inline in code

\- \[ ] Prompt changes are recorded with a version note in the prompt file header

\- \[ ] Agent output is validated before use (schema, format, or grounding check)

\- \[ ] Failure path handled: API error, quota exhaustion, and empty/malformed response

\- \[ ] Where the story involves generated content, output is traceable to its source material



\## 4. Testing



\- \[ ] Unit tests written for new logic and passing locally

\- \[ ] Manual test performed against the acceptance criteria and evidence recorded

\- \[ ] For LLM-facing features, at least one prompt test documented (expected vs actual behaviour)

\- \[ ] Known edge cases and hallucination risks noted in the story comments



\## 5. Documentation \& Tracking



\- \[ ] Jira issue transitioned to \*\*Done\*\* with a closing comment

\- \[ ] Linked GitHub commits visible in the Jira issue development panel

\- \[ ] README or relevant doc updated if setup steps or dependencies changed

\- \[ ] Product Owner has reviewed and accepted the story



\---



\## Notes



This DOD is deliberately fixed for all four sprints so that velocity remains

comparable across iterations. Any change to the DOD must be agreed in a sprint

retrospective and recorded here with the sprint number at which it took effect.

