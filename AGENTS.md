<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **cdut_stu_agents** (2200 symbols, 3008 relationships, 63 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/cdut_stu_agents/context` | Codebase overview, check index freshness |
| `gitnexus://repo/cdut_stu_agents/clusters` | All functional areas |
| `gitnexus://repo/cdut_stu_agents/processes` | All execution flows |
| `gitnexus://repo/cdut_stu_agents/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |
| Work in the Composables area (84 symbols) | `.claude/skills/generated/composables/SKILL.md` |
| Work in the Services area (30 symbols) | `.claude/skills/generated/services/SKILL.md` |
| Work in the Tasks area (24 symbols) | `.claude/skills/generated/tasks/SKILL.md` |
| Work in the Judge area (17 symbols) | `.claude/skills/generated/judge/SKILL.md` |
| Work in the App area (12 symbols) | `.claude/skills/generated/app/SKILL.md` |
| Work in the Scripts area (9 symbols) | `.claude/skills/generated/scripts/SKILL.md` |
| Work in the Cluster_28 area (7 symbols) | `.claude/skills/generated/cluster-28/SKILL.md` |
| Work in the Models area (7 symbols) | `.claude/skills/generated/models/SKILL.md` |
| Work in the Routers area (7 symbols) | `.claude/skills/generated/routers/SKILL.md` |
| Work in the Workers area (6 symbols) | `.claude/skills/generated/workers/SKILL.md` |
| Work in the Repositories area (6 symbols) | `.claude/skills/generated/repositories/SKILL.md` |
| Work in the Prompts area (3 symbols) | `.claude/skills/generated/prompts/SKILL.md` |

<!-- gitnexus:end -->
