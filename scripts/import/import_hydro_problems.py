#!/usr/bin/env python3
"""Import Hydro-format problems into QDUOJ via Admin API.

Hydro format: each problem directory contains:
  - problem.yaml  (pid, title, tag, etc.)
  - problem.md    (HTML description)
  - testdata/     (1.in, 1.out, ..., config.yaml)

This script converts Hydro format to QDUOJ API three-phase pattern:
  1. POST /api/admin/problem  (create with placeholder test_case_id)
  2. POST /api/admin/test_case (upload zip of test data)
  3. PUT  /api/admin/problem  (update with real test_case_id + scores)
"""

import os
import re
import sys
import yaml
import zipfile
import tempfile
import requests
from pathlib import Path
from http.cookiejar import CookieJar

BASE_URL = os.environ.get("OJ_BASE_URL", "http://localhost:8000")
OJ_USER = os.environ.get("OJ_USER", "root")
OJ_PASS = os.environ.get("OJ_PASS", "rootroot")
HYDRO_DIR = os.environ.get("HYDRO_DIR", "")
VISISIBLE = True  # make all imported problems visible

# Default starter templates
TEMPLATES = {
    "C": "#include <stdio.h>\nint main(void){\n    return 0;\n}\n",
    "C++": "#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    return 0;\n}\n",
    "Java": "public class Main {\n    public static void main(String[] args) {\n    }\n}\n",
    "Python3": "def solve():\n    pass\n\nif __name__ == '__main__':\n    solve()\n",
}


def login(base_url, username, password):
    """Authenticate with QDUOJ, return (session, csrf_token)."""
    session = requests.Session()
    # Prime CSRF cookie
    session.get(f"{base_url}/api/profile")
    csrf = session.cookies.get("csrftoken", "")
    if not csrf:
        raise RuntimeError("Failed to get CSRF token from /api/profile")

    # Login
    resp = session.post(
        f"{base_url}/api/login",
        json={"username": username, "password": password},
        headers={"X-CSRFToken": csrf},
    )
    if resp.status_code != 200 or resp.json().get("error"):
        raise RuntimeError(f"Login failed: {resp.status_code} {resp.text}")

    # Get new CSRF after login rotation
    csrf = session.cookies.get("csrftoken", "")
    if not csrf:
        raise RuntimeError("CSRF token missing after login")
    return session, csrf


def parse_hydro_html(html):
    """Parse Hydro problem.md HTML into structured sections.

    Returns dict with keys: description, input_description, output_description,
    hint, sample_input, sample_output.
    """
    parts = re.split(r"<h2>(.*?)</h2>", html)
    # parts: [before_first_h2, title1, content1, title2, content2, ...]
    raw_sections = {}
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        raw_sections[title] = content

    # Map Chinese section titles to field names
    description = ""
    input_description = ""
    output_description = ""
    hint = ""
    sample_input = ""
    sample_output = ""

    for title, content in raw_sections.items():
        if "说明" in title or "描述" in title or "题目" in title:
            description = content
        elif "输入格式" in title or "Input" in title.lower():
            # Extract sample data inline: "输入样例: <br/>2 4<br/> 3 2"
            input_description, si = _extract_inline_sample(content, "输入样例")
            if si:
                sample_input = si
        elif "输出格式" in title or "Output" in title.lower():
            output_description, so = _extract_inline_sample(content, "输出样例")
            if so:
                sample_output = so
        elif "提示" in title or "Hint" in title.lower():
            hint = content
        elif "样例" in title or "Sample" in title.lower():
            # Try extracting from <pre><code> blocks
            codes = re.findall(r'<pre><code[^>]*>(.*?)</code></pre>', content, re.DOTALL)
            if len(codes) >= 2 and not sample_input:
                sample_input = _strip_html_tags(codes[0])
                sample_output = _strip_html_tags(codes[1])
            elif len(codes) >= 1 and not sample_input:
                sample_input = _strip_html_tags(codes[0])

    # Fallback: some Hydro problems have sample data embedded in "说明" section
    # under <b>输入：</b> / <b>输出：</b> tags
    if not sample_input or sample_input == "参考上文":
        desc_raw = raw_sections.get("说明", raw_sections.get("描述", ""))
        # Pattern: <b>输入：</b><br/>data<br/><b>输出：</b><br/>data
        m_in = re.search(r'<b>\s*输入[：:]?\s*</b>(.*?)<b>\s*输出[：:]?\s*</b>', desc_raw, re.DOTALL)
        if m_in:
            sample_input = _strip_html_tags(m_in.group(1)).strip()
            after_output_tag = desc_raw[m_in.end():]
            # Output data: from after </b> until double <br> or <h2> or end of description
            m_end = re.search(r'(<br\s*/?>\s*){2,}|<h2>', after_output_tag)
            if m_end:
                sample_output = _strip_html_tags(after_output_tag[:m_end.start()]).strip()
            else:
                sample_output = _strip_html_tags(after_output_tag).strip()

    # Clean "参考上文" — if sample is still a placeholder, clear it
    if sample_input in ("参考上文", ""):
        sample_input = ""
    if sample_output in ("参考上文", ""):
        sample_output = ""

    return {
        "description": description or "See problem description.",
        "input_description": input_description or "See problem description.",
        "output_description": output_description or "See problem description.",
        "hint": hint,
        "sample_input": sample_input,
        "sample_output": sample_output,
    }


def _extract_inline_sample(content, marker):
    """Extract inline sample data after a marker like '输入样例:' or '输出样例:'.

    Splits content at the marker. Everything before is description,
    everything after (stripped of HTML) is sample text.
    Returns (description_text, sample_text).
    """
    # Try multiple marker patterns
    for pat in [rf"{re.escape(marker)}\s*[:：]\s*", rf"{re.escape(marker)}\s*"]:
        m = re.search(pat, content)
        if m:
            desc_html = content[:m.start()]
            sample_html = content[m.end():]
            desc_text = _strip_html_tags(desc_html).strip()
            sample_text = _strip_html_tags(sample_html).strip()
            # Clean up description-only markers like "输入描述:"
            desc_text = re.sub(r'(输入描述|输出描述)\s*[:：]?\s*', '', desc_text).strip()
            return desc_text, sample_text
    # No marker found — entire content is description
    text = _strip_html_tags(content).strip()
    text = re.sub(r'(输入描述|输出描述)\s*[:：]?\s*', '', text).strip()
    return text, ""


def _strip_html_tags(text):
    """Remove HTML tags and decode common entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return text.strip()


def load_hydro_problem(prob_dir):
    """Load a single Hydro problem directory into a dict."""
    d = Path(prob_dir)
    with open(d / "problem.yaml", "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    with open(d / "problem.md", "r", encoding="utf-8") as f:
        html = f.read()

    # Parse HTML into structured fields
    parsed = parse_hydro_html(html)

    # Build QDUOJ sample list
    samples = []
    if parsed["sample_input"] and parsed["sample_output"]:
        samples.append({
            "input": parsed["sample_input"],
            "output": parsed["sample_output"],
        })

    # Extract tags - filter out internal metadata tags (price::X, source::X)
    tags = []
    for t in meta.get("tag", []):
        if "::" not in t:
            tags.append(t)
    if not tags:
        tags = ["蓝桥杯"]

    # Load test cases
    testdata_dir = d / "testdata"
    test_cases = []
    config = {}
    if (testdata_dir / "config.yaml").exists():
        with open(testdata_dir / "config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Find all ordered test case pairs
    in_files = sorted(
        [f for f in os.listdir(testdata_dir) if f.endswith(".in")],
        key=lambda x: int(x.replace(".in", "")),
    )
    for in_file in in_files:
        base = in_file.replace(".in", "")
        out_file = base + ".out"
        in_path = testdata_dir / in_file
        out_path = testdata_dir / out_file
        if out_path.exists():
            with open(in_path, "r", encoding="utf-8", errors="replace") as f:
                inp = f.read()
            with open(out_path, "r", encoding="utf-8", errors="replace") as f:
                outp = f.read()
            test_cases.append({
                "input_name": in_file,
                "output_name": out_file,
                "input": inp,
                "output": outp,
            })

    # Extract time/memory from config
    time_limit = config.get("time", "1000ms")
    memory_limit = config.get("memory", "512m")
    if isinstance(time_limit, str):
        time_limit = int(time_limit.lower().replace("ms", "").replace("s", "000").strip())
    else:
        time_limit = int(time_limit)
    if isinstance(memory_limit, str):
        ml = memory_limit.lower().replace("mb", "").replace("m", "").replace("gb", "000").strip()
        memory_limit = int(ml)
    else:
        memory_limit = int(memory_limit)

    return {
        "pid": meta.get("pid", ""),
        "title": meta.get("title", ""),
        "description": parsed["description"],
        "input_description": parsed["input_description"],
        "output_description": parsed["output_description"],
        "hint": parsed["hint"],
        "samples": samples,
        "tags": tags,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "test_cases": test_cases,
    }


def create_problem(session, base_url, csrf, prob, display_id):
    """Phase 1: Create problem via API."""
    # Build sample list for QDUOJ — API requires at least one sample
    sample_list = []
    for s in prob.get("samples", []):
        if s.get("input") and s.get("output"):
            sample_list.append({"input": s["input"], "output": s["output"]})
    # Fallback: use first test case as sample if no sample extracted from description
    if not sample_list and prob.get("test_cases"):
        tc = prob["test_cases"][0]
        sample_list.append({"input": tc["input"].strip(), "output": tc["output"].strip()})

    # Build placeholder test_case_score for creation (will be updated in Phase 3)
    n_cases = len(prob["test_cases"])
    if n_cases > 0:
        score_each = 100 // n_cases
        placeholder_scores = []
        for i in range(n_cases):
            s = score_each if i < n_cases - 1 else (100 - score_each * (n_cases - 1))
            placeholder_scores.append({
                "score": s,
                "input_name": prob["test_cases"][i]["input_name"],
                "output_name": prob["test_cases"][i]["output_name"],
            })
    else:
        placeholder_scores = []

    payload = {
        "_id": display_id,
        "title": prob["title"],
        "description": prob["description"],
        "input_description": prob["input_description"],
        "output_description": prob["output_description"],
        "samples": sample_list,
        "hint": prob.get("hint", ""),
        "test_case_id": "0" * 32,  # placeholder
        "test_case_score": placeholder_scores,
        "languages": ["C", "C++", "Java", "Python3"],
        "rule_type": "ACM",
        "io_mode": {"input": "input.txt", "output": "output.txt", "io_mode": "Standard IO"},
        "time_limit": prob["time_limit"],
        "memory_limit": prob["memory_limit"],
        "spj": False,
        "spj_language": None,
        "spj_code": None,
        "spj_version": "",
        "spj_compile_ok": False,
        "tags": prob["tags"],
        "share_submission": False,
        "visible": VISISIBLE,
        "is_public": True,
        "difficulty": "Mid",
        "source": "蓝桥杯",
        "template": TEMPLATES,
    }
    resp = session.post(
        f"{base_url}/api/admin/problem",
        json=payload,
        headers={"X-CSRFToken": csrf},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Create problem failed: {resp.status_code} {resp.text}")
    data = resp.json()
    if "error" in data and data["error"]:
        raise RuntimeError(f"Create problem error: {data}")
    return data.get("data", data)


def upload_test_cases(session, base_url, csrf, problem_db_id, prob):
    """Phase 2: Upload test case ZIP."""
    # Build zip in memory
    tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with zipfile.ZipFile(tmp.name, "w") as zf:
            for tc in prob["test_cases"]:
                zf.writestr(tc["input_name"], tc["input"])
                zf.writestr(tc["output_name"], tc["output"])
        # Upload
        with open(tmp.name, "rb") as f:
            files = {"file": ("testdata.zip", f, "application/zip")}
            data = {"problem_id": str(problem_db_id), "spj": "false"}
            resp = session.post(
                f"{base_url}/api/admin/test_case",
                files=files,
                data=data,
                headers={"X-CSRFToken": csrf},
            )
    finally:
        os.unlink(tmp.name)

    if resp.status_code != 200:
        raise RuntimeError(f"Upload test cases failed: {resp.status_code} {resp.text}")
    result = resp.json()
    if "error" in result and result["error"]:
        raise RuntimeError(f"Upload test cases error: {result}")
    return result.get("data", result)


def update_problem(session, base_url, csrf, prob, problem_db_id, display_id, real_tc_id, uploaded_info):
    """Phase 3: Update problem with real test_case_id and scores."""
    # Build test_case_score from uploaded info
    n = len(prob["test_cases"])
    score_each = 100 // n
    scores = []
    for i, tc in enumerate(prob["test_cases"]):
        s = score_each if i < n - 1 else (100 - score_each * (n - 1))
        scores.append({
            "score": s,
            "input_name": tc["input_name"],
            "output_name": tc["output_name"],
        })

    # Build sample list for QDUOJ — API requires at least one sample
    sample_list = []
    for s in prob.get("samples", []):
        if s.get("input") and s.get("output"):
            sample_list.append({"input": s["input"], "output": s["output"]})
    if not sample_list and prob.get("test_cases"):
        tc = prob["test_cases"][0]
        sample_list.append({"input": tc["input"].strip(), "output": tc["output"].strip()})

    payload = {
        "id": problem_db_id,
        "_id": display_id,
        "title": prob["title"],
        "description": prob["description"],
        "input_description": prob["input_description"],
        "output_description": prob["output_description"],
        "samples": sample_list,
        "hint": prob.get("hint", ""),
        "test_case_id": real_tc_id,
        "test_case_score": scores,
        "languages": ["C", "C++", "Java", "Python3"],
        "rule_type": "ACM",
        "io_mode": {"input": "input.txt", "output": "output.txt", "io_mode": "Standard IO"},
        "time_limit": prob["time_limit"],
        "memory_limit": prob["memory_limit"],
        "spj": False,
        "spj_language": None,
        "spj_code": None,
        "spj_version": "",
        "spj_compile_ok": False,
        "tags": prob["tags"],
        "share_submission": False,
        "visible": VISISIBLE,
        "is_public": True,
        "difficulty": "Mid",
        "source": "蓝桥杯",
        "template": TEMPLATES,
    }
    resp = session.put(
        f"{base_url}/api/admin/problem",
        json=payload,
        headers={"X-CSRFToken": csrf},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Update problem failed: {resp.status_code} {resp.text}")
    data = resp.json()
    if "error" in data and data["error"]:
        raise RuntimeError(f"Update problem error: {data}")
    return data


def import_hydro_problem(session, base_url, csrf, prob, display_id):
    """Full three-phase import for a single problem."""
    # Phase 1: Create
    create_result = create_problem(session, base_url, csrf, prob, display_id)
    problem_db_id = create_result.get("id") if isinstance(create_result, dict) else create_result
    print(f"  Phase 1: Created problem db_id={problem_db_id}, display_id={display_id}")

    # Phase 2: Upload test cases
    upload_result = upload_test_cases(session, base_url, csrf, problem_db_id, prob)
    # Upload returns {"id": "<test_case_id>", "info": [...], "spj": False}
    real_tc_id = upload_result.get("id", "") or upload_result.get("test_case_id", "")
    uploaded_info = upload_result.get("info", [])
    print(f"  Phase 2: Uploaded {len(prob['test_cases'])} test cases, tc_id={real_tc_id[:12]}...")

    # Phase 3: Update
    update_result = update_problem(
        session, base_url, csrf, prob, problem_db_id, display_id, real_tc_id, uploaded_info
    )
    print(f"  Phase 3: Updated problem with real test_case_id and scores")

    return problem_db_id


def main():
    if not HYDRO_DIR:
        print("Usage: HYDRO_DIR=/path/to/export python import_hydro_problems.py")
        sys.exit(1)

    export_dir = Path(HYDRO_DIR)
    if not export_dir.exists():
        print(f"Error: {HYDRO_DIR} does not exist")
        sys.exit(1)

    # Find all problem directories (those with problem.yaml)
    prob_dirs = sorted([
        d for d in export_dir.iterdir()
        if d.is_dir() and (d / "problem.yaml").exists()
    ])

    if not prob_dirs:
        print(f"No Hydro problem directories found in {HYDRO_DIR}")
        sys.exit(1)

    print(f"Found {len(prob_dirs)} Hydro problems to import")
    print(f"Connecting to QDUOJ at {BASE_URL}...")

    session, csrf = login(BASE_URL, OJ_USER, OJ_PASS)
    print(f"Logged in as {OJ_USER}")

    success = 0
    failed = 0
    for prob_dir in prob_dirs:
        try:
            prob = load_hydro_problem(prob_dir)
            display_id = prob["pid"]
            print(f"\nImporting [{display_id}] {prob['title']}...")
            db_id = import_hydro_problem(session, BASE_URL, csrf, prob, display_id)
            print(f"  SUCCESS: {display_id} -> db_id={db_id}")
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Import complete: {success} success, {failed} failed, {len(prob_dirs)} total")


if __name__ == "__main__":
    main()