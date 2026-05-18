"""Classifiers and fix-applicators for the problem auditor.

Handles template-markers wrapping, quick heuristic checks, default
templates, and applies LLM-suggested fixes to problem records.
"""

from __future__ import annotations

import logging
import re as _re

from app.tasks.audit.db import update_problem

logger = logging.getLogger("ai-agent-lite.audit.classifier")


# ── default starter-code templates ────────────────────────────────────

DEFAULT_TEMPLATES = {
    "C": (
        "//PREPEND BEGIN\n"
        "#include <stdio.h>\n"
        "//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "int solve(int n) {\n"
        "    // TODO: implement and return result\n"
        "    return 0;\n"
        "}\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "int main(void) {\n"
        "    int n; scanf(\"%d\", &n);\n"
        "    printf(\"%d\\n\", solve(n));\n"
        "    return 0;\n"
        "}\n"
        "//APPEND END\n"
    ),
    "C++": (
        "//PREPEND BEGIN\n"
        "#include <bits/stdc++.h>\n"
        "using namespace std;\n"
        "//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "int solve(int n) {\n"
        "    // TODO: implement and return result\n"
        "    return 0;\n"
        "}\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "int main() {\n"
        "    ios::sync_with_stdio(false); cin.tie(nullptr);\n"
        "    int n; cin >> n;\n"
        "    cout << solve(n) << endl; return 0;\n"
        "}\n"
        "//APPEND END\n"
    ),
    "Java": (
        "//PREPEND BEGIN\n"
        "import java.util.*;\n\n"
        "public class Main {\n"
        "//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "    public static int solve(int n) {\n"
        "        // TODO: implement and return result\n"
        "        return 0;\n"
        "    }\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "    public static void main(String[] args) {\n"
        "        Scanner sc = new Scanner(System.in);\n"
        "        int n = sc.nextInt();\n"
        "        System.out.println(solve(n));\n"
        "    }\n"
        "}\n"
        "//APPEND END\n"
    ),
    "Python3": (
        "//PREPEND BEGIN\n\n//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "def solve(n: int) -> int:\n"
        "    # TODO: implement and return result\n"
        "    return 0\n\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "if __name__ == '__main__':\n"
        "    n = int(input())\n"
        "    print(solve(n))\n"
        "//APPEND END\n"
    ),
}


# ── quick heuristic pre-check ─────────────────────────────────────────

def quick_check(problem: dict) -> list[str]:
    """Fast heuristic pre-check of a problem record."""
    issues = []
    if not problem.get("title") or not problem["title"].strip():
        issues.append("Missing or empty title")
    desc = problem.get("description") or ""
    if not desc.strip() or len(desc.strip()) < 10:
        issues.append("Description too short or empty")
    samples = problem.get("samples") or []
    if not samples:
        issues.append("No sample input/output")

    template = problem.get("template") or {}
    for lang in ("C", "C++", "Java", "Python3"):
        code = template.get(lang, "") or ""
        if not code.strip():
            issues.append(f"Missing starter code for {lang}")
        elif "//TEMPLATE BEGIN" not in code:
            issues.append(f"Starter code lacks markers for {lang}")
        elif _re.search(r'void\s+solve\s*\(\s*(void)?\s*\)', code):
            issues.append(
                f"void solve(void) in {lang} — "
                f"solve() must take params and return result",
            )

    if not (problem.get("test_case_id") or "").strip():
        issues.append("Empty test_case_id")
    return issues


# ── template-marker wrapping ──────────────────────────────────────────

def ensure_template_markers(code: str, lang: str) -> str:
    """Wrap bare code into //PREPEND/TEMPLATE/APPEND marker format."""
    if "//TEMPLATE BEGIN" in code:
        return code

    lines = code.split("\n")

    if lang == "Python3":
        return _wrap_python(lines)
    elif lang in ("C", "C++"):
        return _wrap_c_family(lines)
    elif lang == "Java":
        return _wrap_java(lines)

    # unknown: everything in TEMPLATE
    return (
        "//PREPEND BEGIN\n\n//PREPEND END\n\n"
        f"//TEMPLATE BEGIN\n{code}\n//TEMPLATE END\n\n"
        "//APPEND BEGIN\n\n//APPEND END"
    )


def _wrap_python(lines: list[str]) -> str:
    prepend_lines = []
    template_lines = []
    append_lines = []
    in_append = False

    for line in lines:
        s = line.strip()
        if s.startswith("if __name__") or s == "if __name__ == '__main__':":
            in_append = True
            append_lines.append(line)
            continue
        if in_append:
            append_lines.append(line)
            continue
        if s in ("import sys",) or s.startswith("import sys #"):
            continue
        if not template_lines and s.startswith("def solve"):
            template_lines.append(line)
            continue
        if template_lines:
            template_lines.append(line)
        else:
            prepend_lines.append(line)

    pre = "\n".join(prepend_lines).strip()
    tpl = "\n".join(template_lines)
    app = "\n".join(append_lines)
    return (
        f"//PREPEND BEGIN\n{pre}\n//PREPEND END\n\n"
        f"//TEMPLATE BEGIN\n{tpl}\n//TEMPLATE END\n\n"
        f"//APPEND BEGIN\n{app}\n//APPEND END"
    )


def _wrap_c_family(lines: list[str]) -> str:
    prepend_lines, template_lines, append_lines = [], [], []
    in_append = False
    for line in lines:
        s = line.strip()
        if s.startswith("int main("):
            in_append = True
            append_lines.append(line)
            continue
        if in_append:
            append_lines.append(line)
            continue
        if not template_lines and (
            s.startswith("void solve") or s.startswith("int solve")
        ):
            template_lines.append(line)
            continue
        if template_lines:
            template_lines.append(line)
        else:
            prepend_lines.append(line)

    pre = "\n".join(prepend_lines)
    tpl = "\n".join(template_lines)
    app = "\n".join(append_lines)
    return (
        f"//PREPEND BEGIN\n{pre}\n//PREPEND END\n\n"
        f"//TEMPLATE BEGIN\n{tpl}\n//TEMPLATE END\n\n"
        f"//APPEND BEGIN\n{app}\n//APPEND END"
    )


def _wrap_java(lines: list[str]) -> str:
    prepend_lines, template_lines, append_lines = [], [], []
    in_template, in_append, depth = False, False, 0
    for line in lines:
        s = line.strip()
        if s.startswith("public static") and "solve" in s:
            in_template = True
            depth = 0
            template_lines.append(line)
            depth += line.count("{") - line.count("}")
            continue
        if in_template and not in_append:
            template_lines.append(line)
            depth += line.count("{") - line.count("}")
            if depth <= 0 and "{" in "".join(template_lines):
                in_template = False
            continue
        if s.startswith("public static void main"):
            in_append = True
        if in_append:
            append_lines.append(line)
        else:
            prepend_lines.append(line)

    pre = "\n".join(prepend_lines)
    tpl = "\n".join(template_lines)
    app = "\n".join(append_lines)
    return (
        f"//PREPEND BEGIN\n{pre}\n//PREPEND END\n\n"
        f"//TEMPLATE BEGIN\n{tpl}\n//TEMPLATE END\n\n"
        f"//APPEND BEGIN\n{app}\n//APPEND END"
    )


# ── fix application ───────────────────────────────────────────────────

def apply_fixes(problem: dict, fixes: dict) -> None:
    """Apply LLM-suggested fixes via direct PostgreSQL writes."""
    updated = dict(problem)

    if fixes.get("template"):
        merged = dict(updated.get("template") or {})
        for lang, code in fixes["template"].items():
            if code and isinstance(code, str):
                merged[lang] = ensure_template_markers(code, lang)
        for lang in ("C", "C++", "Java", "Python3"):
            if lang not in fixes["template"] or not fixes["template"].get(lang):
                existing = merged.get(lang, "") or ""
                if existing.strip() and "//TEMPLATE BEGIN" not in existing:
                    merged[lang] = ensure_template_markers(existing, lang)
        updated["template"] = merged

    for field in (
        "title", "description", "input_description",
        "output_description", "hint",
    ):
        if fixes.get(field):
            updated[field] = fixes[field]

    if fixes.get("samples"):
        updated["samples"] = fixes["samples"]
    if fixes.get("difficulty"):
        updated["difficulty"] = fixes["difficulty"]
    if fixes.get("source"):
        updated["source"] = fixes["source"]
    if fixes.get("tags"):
        updated["tags"] = fixes["tags"]

    for required in (
        "_id", "id", "test_case_id", "io_mode", "languages",
        "rule_type", "spj", "visible",
    ):
        if required not in updated and required in problem:
            updated[required] = problem[required]

    ok = update_problem(updated)
    if not ok:
        raise RuntimeError(
            f"PostgreSQL update failed for _id={updated.get('_id')}",
        )
