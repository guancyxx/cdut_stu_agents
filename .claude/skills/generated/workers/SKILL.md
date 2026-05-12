---
name: workers
description: "Skill for the Workers area of cdut_stu_agents. 6 symbols across 6 files."
---

# Workers

6 symbols | 6 files | Cohesion: 100%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how ProblemAnalyzerAgent, LearningPartnerAgent, LearningManagerAgent work
- Modifying workers-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/app/workers/problem_analyzer.py` | ProblemAnalyzerAgent |
| `ai-agent-lite/app/workers/learning_partner.py` | LearningPartnerAgent |
| `ai-agent-lite/app/workers/learning_manager.py` | LearningManagerAgent |
| `ai-agent-lite/app/workers/contest_coach.py` | ContestCoachAgent |
| `ai-agent-lite/app/workers/code_reviewer.py` | CodeReviewerAgent |
| `ai-agent-lite/app/workers/base.py` | BaseWorker |

## Entry Points

Start here when exploring this area:

- **`ProblemAnalyzerAgent`** (Class) — `ai-agent-lite/app/workers/problem_analyzer.py:13`
- **`LearningPartnerAgent`** (Class) — `ai-agent-lite/app/workers/learning_partner.py:14`
- **`LearningManagerAgent`** (Class) — `ai-agent-lite/app/workers/learning_manager.py:14`
- **`ContestCoachAgent`** (Class) — `ai-agent-lite/app/workers/contest_coach.py:13`
- **`CodeReviewerAgent`** (Class) — `ai-agent-lite/app/workers/code_reviewer.py:28`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ProblemAnalyzerAgent` | Class | `ai-agent-lite/app/workers/problem_analyzer.py` | 13 |
| `LearningPartnerAgent` | Class | `ai-agent-lite/app/workers/learning_partner.py` | 14 |
| `LearningManagerAgent` | Class | `ai-agent-lite/app/workers/learning_manager.py` | 14 |
| `ContestCoachAgent` | Class | `ai-agent-lite/app/workers/contest_coach.py` | 13 |
| `CodeReviewerAgent` | Class | `ai-agent-lite/app/workers/code_reviewer.py` | 28 |
| `BaseWorker` | Class | `ai-agent-lite/app/workers/base.py` | 10 |

## How to Explore

1. `gitnexus_context({name: "ProblemAnalyzerAgent"})` — see callers and callees
2. `gitnexus_query({query: "workers"})` — find related execution flows
3. Read key files listed above for implementation details
