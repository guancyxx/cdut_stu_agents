"""LLM provider abstraction and prompt builder for the problem auditor.

Dispatches to the configured audit LLM provider and builds structured prompts.
"""

from __future__ import annotations

import json
import logging
import re as _re

import httpx

from app.config import settings

logger = logging.getLogger("ai-agent-lite.audit.llm")


# ── system prompt ──────────────────────────────────────────────────────

AUDIT_SYSTEM_PROMPT = """You are an expert competitive-programming problem curator and auditor for a university-level Online Judge (OJ).

Your job is to evaluate and FIX a problem JSON. You receive the full database record.
You must do ALL of the following in ONE pass:

## 1. LOCAL-ONLY ID Check
Only problems with `_id` starting with `custom-` are local. Skip others.

## 2. Deduplicate Boilerplate / Garbage
Look for and REMOVE these patterns from `description` / `input_description` / `output_description`:
- Lines like "例五、输入……例六、输出……", "样例五", "例3、", "输入样例5", any numbered examples beyond the first
- Repeated placeholder text like "Button", "???", "暂无"
- HTML residue: `<br>`, `<p>`, `&nbsp;`, `&#039;`
- Any sentence that is NOT part of the actual problem statement

## 3. Non-OJ Content Detection (CRITICAL)
If the problem is NOT an algorithmic/programming problem, flag it as `"status": "remove"` with `"reason"`.
Non-OJ content includes:
- "输出一首古诗" / "打印九九乘法表" / "print a poem"
- Anything asking to output art, poems, ASCII pictures
- Trivial print statements with no algorithmic thinking
- Problems that can be solved with a single `print("...")` without input processing

## 4. Complete Structure Enforcement
Every VALID problem MUST have:
- `title`: clear, no trailing spaces, no NBSP
- `description`: full problem text (story + task), cleaned, >= 50 chars
- `input_description`: input format specification
- `output_description`: output format specification
- `samples`: at least 1 {input, output} pair with real data
- `hint`: optional but encouraged

## 5. Difficulty Reclassification (REQUIRED)
IGNORE the existing `difficulty` field. Re-evaluate based on:
- **Low**: simple arithmetic, conditionals, basic loops, no data structures
- **Mid**: arrays, sorting, greedy, basic DP, binary search, strings, hashing
- **High**: complex DP, graph algorithms (BFS/DFS/Dijkstra/MST), segment trees, advanced math, flow

## 6. Algorithm Tag Assignment (REQUIRED)
Provide at least 1-3 tags from this list (or related terms):
排序, 二分, 搜索, DP/动态规划, 贪心, 图论, 并查集, 最短路, 树, 线段树,
字符串, 哈希, 数学, 数论, 模拟, 枚举, 递归, 回溯, 分治, 前缀和,
差分, 双指针, 滑动窗口, 单调栈, 位运算, 组合数学, 博弈论, 计算几何

## 7. Starter Code Templates (MUST use markers)
For EVERY language (C, C++, Java, Python3), produce or verify templates using:
```
//PREPEND BEGIN
<#include / imports / class opening>
//PREPEND END

//TEMPLATE BEGIN
<solve() with typed params + return type, NO I/O>
//TEMPLATE END

//APPEND BEGIN
<main() reads input, calls solve(), prints return>
//APPEND END
```

CRITICAL RULES:
- All languages use `//` markers (even Python3)
- solve() takes typed parameters, returns value, does NO I/O
- main() reads stdin, calls solve(), prints result
- Template must match the problem's actual input format from `input_description`
- Include `# Example: solve(arg1, arg2) -> expected_output`

## 8. Metadata
- `source`: leave as-is unless empty, then set to "CDUT OJ"
- `languages`: must include ["C","C++","Java","Python3"]
- `time_limit` and `memory_limit`: keep existing

## Response Format
Output ONLY this JSON, no markdown fences, no text before/after:

{
  "status": "pass|fail|remove",
  "reason": "if remove: why this is not an OJ problem",
  "issues": ["list of specific issues found, empty if pass"],
  "fixes": {
    "title": "cleaned title or null",
    "description": "cleaned description with garbage removed or null",
    "input_description": "cleaned or null",
    "output_description": "cleaned or null",
    "hint": "hint text or null",
    "samples": [{"input": "...", "output": "..."}],
    "difficulty": "Low|Mid|High",
    "tags": ["tag1", "tag2", "tag3"],
    "source": "CDUT OJ or existing",
    "template": {
      "C": "full C template with //PREPEND/TEMPLATE/APPEND markers or null",
      "C++": "full C++ template with markers or null",
      "Java": "full Java template with markers or null",
      "Python3": "full Python3 template with markers or null"
    }
  }
}

If status is "pass", put nulls in fixes. If "remove", fixes can be empty.
For "fail", provide corrections for every issue found.
"""


# ── prompt builder ─────────────────────────────────────────────────────

def build_audit_prompt(problem: dict) -> str:
    """Build user prompt with the problem data serialised as JSON."""
    problem_data = json.dumps(problem, ensure_ascii=False, indent=2)
    return f"Audit the following problem:\n\n{problem_data}"


# ── LLM call dispatch ─────────────────────────────────────────────────

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Send a completion request to the configured audit LLM provider."""
    provider = settings.audit_llm_provider

    if provider == "xiaomi":
        return _call_xiaomi(system_prompt, user_prompt)
    elif provider == "ollama":
        return _call_ollama(system_prompt, user_prompt)
    else:
        raise ValueError(f"Unknown audit LLM provider: {provider}")


def _call_xiaomi(system_prompt: str, user_prompt: str) -> str:
    """Call Xiaomi MiniMax (OpenAI-compatible) endpoint.

    mimo-v2-pro is a thinking model — output goes to reasoning_content,
    not content. We fall back when content is empty.
    """
    url = settings.audit_llm_base_url
    headers = {
        "Authorization": f"Bearer {settings.audit_llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.audit_llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 32768,
        "stream": False,
    }
    with httpx.Client(timeout=settings.audit_llm_timeout) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        if not content.strip():
            content = msg.get("reasoning_content", "") or ""
        return _strip_fences(content)


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    """Call local Ollama instance (GPU inference)."""
    base = settings.audit_llm_base_url.rstrip("/chat/completions")
    if base.endswith("/v1"):
        base = base[:-3]
    url = base.rstrip("/") + "/api/chat"
    combined = f"{system_prompt}\n\n---\n\n{user_prompt}"
    payload = {
        "model": settings.audit_llm_model,
        "messages": [{"role": "user", "content": combined}],
        "stream": False,
        "keep_alive": "0",
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 16384},
    }
    with httpx.Client(timeout=settings.audit_llm_timeout) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        content = msg.get("content", "") or msg.get("thinking", "")
        return _strip_fences(content)


def _strip_fences(content: str) -> str:
    """Remove markdown code-fence wrappers from LLM output."""
    content = content or ""
    content = _re.sub(r'^```(?:json)?\s*\n?', '', content.strip())
    content = _re.sub(r'\n?```\s*$', '', content)
    return content.strip()


# ── response parser ────────────────────────────────────────────────────

def parse_llm_response(raw: str) -> dict:
    """Extract JSON from LLM response string."""
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            result = json.loads(raw[start:end])
            if "status" in result:
                return result
        except json.JSONDecodeError:
            pass
    logger.warning(
        "LLM response was not valid JSON; raw preview: %s", raw[:200],
    )
    return {
        "status": "error",
        "issues": ["LLM response was not valid JSON"],
        "fixes": {},
    }
