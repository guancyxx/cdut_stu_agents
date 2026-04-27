"""
Dry-run test: audit one problem via Ollama and print the result.
Does NOT write to DB or OJ — read-only validation.

Usage:
    python scripts/test_audit_single.py [display_id]
    python scripts/test_audit_single.py           # picks first unaudited
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tasks.problem_auditor import (
    _oj_login,
    _fetch_problem_list,
    _fetch_problem_detail,
    _build_audit_prompt,
    _call_ollama,
    _parse_llm_response,
    _ensure_template_markers,
)


def check_template(lang: str, code: str) -> list[str]:
    issues = []
    if not code or not code.strip():
        issues.append("EMPTY")
        return issues
    if "//TEMPLATE BEGIN" not in code:
        issues.append("NO MARKERS")
    if "//PREPEND BEGIN" not in code:
        issues.append("NO PREPEND")
    if "//APPEND BEGIN" not in code:
        issues.append("NO APPEND")
    if "// Sample:" not in code and "# Sample:" not in code:
        issues.append("NO SAMPLE COMMENT")
    if "// TODO" not in code and "# TODO" not in code:
        issues.append("NO TODO COMMENT")
    if lang == "Python3" and "sys.stdin" in code:
        issues.append("USES sys.stdin (should use input())")
    if lang == "Python3" and "import sys" in code:
        issues.append("HAS import sys (not needed)")
    return issues


def main():
    target_id = sys.argv[1] if len(sys.argv) > 1 else None

    print("Logging into OJ...")
    client, csrf = _oj_login()

    if target_id:
        print(f"Fetching problem list to find db_id for {target_id}...")
        problems = _fetch_problem_list(client, csrf, limit=200)
        match = next((p for p in problems if p["_id"] == target_id), None)
        if not match:
            print(f"Problem {target_id} not found in first 200 problems")
            client.close()
            return
        problem_summary = match
    else:
        print("Fetching problem list (first 100)...")
        problems = _fetch_problem_list(client, csrf, limit=100)
        problem_summary = problems[0] if problems else None

    if not problem_summary:
        print("No problems found")
        client.close()
        return

    display_id = problem_summary["_id"]
    db_id = problem_summary["id"]
    print(f"\nTarget: _id={display_id}  db_id={db_id}  title={problem_summary.get('title', '?')}")

    print("\nFetching full problem detail...")
    problem = _fetch_problem_detail(client, csrf, db_id)
    client.close()

    if not problem:
        print("Failed to fetch problem detail")
        return

    print(f"  title:             {problem.get('title')}")
    print(f"  input_description: {str(problem.get('input_description', ''))[:100]}")
    print(f"  output_description:{str(problem.get('output_description', ''))[:100]}")
    samples = problem.get("samples") or []
    if samples:
        print(f"  sample[0] input:   {str(samples[0].get('input',''))[:80]}")
        print(f"  sample[0] output:  {str(samples[0].get('output',''))[:80]}")

    existing_template = problem.get("template") or {}
    print(f"\nExisting templates: {list(existing_template.keys())}")
    for lang in ("C", "C++", "Java", "Python3"):
        code = existing_template.get(lang, "") or ""
        has_markers = "//TEMPLATE BEGIN" in code
        print(f"  {lang:8s}: {'has markers' if has_markers else 'NO MARKERS'} | len={len(code)}")

    print("\n" + "="*60)
    print("Building prompt and calling Ollama (this may take 1-3 minutes)...")
    print("="*60)

    prompt = _build_audit_prompt(problem)
    print(f"Prompt length: {len(prompt)} chars")

    raw = _call_ollama(prompt)
    print(f"\nRaw LLM response length: {len(raw)} chars")
    print("\n--- RAW RESPONSE (first 500 chars) ---")
    print(raw[:500])
    print("...")

    result = _parse_llm_response(raw)
    print("\n--- PARSED RESULT ---")
    print(f"status: {result.get('status')}")
    print(f"issues: {result.get('issues', [])}")

    fixes = result.get("fixes") or {}
    tmpl_fixes = fixes.get("template") or {}

    print("\n--- TEMPLATE FIX ANALYSIS ---")
    all_ok = True
    for lang in ("C", "C++", "Java", "Python3"):
        code = tmpl_fixes.get(lang) or ""
        if not code:
            print(f"  {lang:8s}: null (no fix provided)")
            continue
        issues = check_template(lang, code)
        status = "OK" if not issues else f"ISSUES: {issues}"
        print(f"  {lang:8s}: {status}")
        if issues:
            all_ok = False

        # Show TEMPLATE section content
        start = code.find("//TEMPLATE BEGIN")
        end = code.find("//TEMPLATE END")
        if start >= 0 and end > start:
            template_section = code[start+len("//TEMPLATE BEGIN"):end].strip()
            print(f"           TEMPLATE section:\n{_indent(template_section, 11)}")
        else:
            print(f"           (no TEMPLATE section found)")
            all_ok = False

    print("\n" + "="*60)
    if all_ok and tmpl_fixes:
        print("RESULT: PASS — templates have correct markers, sample comment, and TODO")
    elif not tmpl_fixes:
        print(f"RESULT: status={result.get('status')} — no template fixes generated (may be pass)")
    else:
        print("RESULT: ISSUES FOUND — see above")
    print("="*60)


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


if __name__ == "__main__":
    main()
