#!/usr/bin/env python3
"""
Import 10 well-designed problems into QDUOJ via Admin API.

Steps:
1. Login and get CSRF
2. For each problem: POST /api/admin/problem, then POST /api/admin/test_case, then PUT /api/admin/problem with real test_case_id
3. Verify via GET /api/problem

Usage:
    python3 import_10_problems.py
"""
import os
import sys
import json
import random
import string
import tempfile
import zipfile

import requests

OJ_URL = os.environ.get("OJ_URL", "http://localhost:8000")
ADMIN_USER = os.environ.get("OJ_ADMIN", "root")
ADMIN_PASS = os.environ.get("OJ_PASS", "rootroot")

PROBLEMS = [
    {
        "title": "Sum of Digits",
        "description": "<p>Given a non-negative integer <strong>n</strong>, calculate the sum of its digits.</p><p>For example, the sum of digits of 12345 is 1+2+3+4+5=15.</p>",
        "input_description": "<p>A single non-negative integer <strong>n</strong> (0 &lt;= n &lt;= 10<sup>9</sup>).</p>",
        "output_description": "<p>Output a single integer: the sum of digits of <strong>n</strong>.</p>",
        "samples": [{"input": "12345", "output": "15"}],
        "hint": "<p>Use modulo and division to extract each digit.</p>",
        "test_cases": [
            {"input": "12345\n", "output": "15\n"},
            {"input": "0\n", "output": "0\n"},
            {"input": "999999999\n", "output": "81\n"},
            {"input": "1000000000\n", "output": "1\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
        "tags": ["Math"], "source": "Custom",
    },
    {
        "title": "Vowel Count",
        "description": "<p>Given a string consisting of English letters only (both uppercase and lowercase), count the number of vowels in it.</p><p>Vowels are: a, e, i, o, u (both uppercase and lowercase count).</p>",
        "input_description": "<p>A single line containing a string <strong>s</strong> (1 &lt;= |s| &lt;= 1000), consisting only of English letters.</p>",
        "output_description": "<p>Output a single integer: the number of vowels in <strong>s</strong>.</p>",
        "samples": [{"input": "HelloWorld", "output": "3"}],
        "hint": "<p>Check each character against the set of vowels.</p>",
        "test_cases": [
            {"input": "HelloWorld\n", "output": "3\n"},
            {"input": "AEIOU\n", "output": "5\n"},
            {"input": "bcdfg\n", "output": "0\n"},
            {"input": "AbCdEfGhIj\n", "output": "3\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
        "tags": ["String"], "source": "Custom",
    },
    {
        "title": "Leap Year",
        "description": "<p>Given a year, determine whether it is a leap year.</p><p>A leap year is divisible by 4 but NOT by 100, unless it is also divisible by 400.</p>",
        "input_description": "<p>A single integer <strong>y</strong> (1582 &lt;= y &lt;= 9999), the year.</p>",
        "output_description": "<p>Output <strong>Yes</strong> if it is a leap year, otherwise <strong>No</strong>.</p>",
        "samples": [{"input": "2000", "output": "Yes"}, {"input": "1900", "output": "No"}],
        "hint": "<p>2000 is a leap year (divisible by 400), 1900 is not (divisible by 100 but not 400).</p>",
        "test_cases": [
            {"input": "2000\n", "output": "Yes\n"},
            {"input": "1900\n", "output": "No\n"},
            {"input": "2024\n", "output": "Yes\n"},
            {"input": "2023\n", "output": "No\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
        "tags": ["Math"], "source": "Custom",
    },
    {
        "title": "Find the Maximum",
        "description": "<p>Given <strong>n</strong> integers, find the maximum value and its position (1-indexed). If there are multiple occurrences of the maximum, output the position of the first one.</p>",
        "input_description": "<p>The first line contains an integer <strong>n</strong> (1 &lt;= n &lt;= 1000). The second line contains <strong>n</strong> integers, each between -10<sup>9</sup> and 10<sup>9</sup>.</p>",
        "output_description": "<p>Output two integers separated by a space: the maximum value and its 1-indexed position.</p>",
        "samples": [{"input": "5\n3 7 2 7 1", "output": "7 2"}],
        "hint": "<p>Keep track of the maximum and its index while scanning the array.</p>",
        "test_cases": [
            {"input": "5\n3 7 2 7 1\n", "output": "7 2\n"},
            {"input": "1\n-5\n", "output": "-5 1\n"},
            {"input": "3\n10 10 10\n", "output": "10 1\n"},
            {"input": "6\n-1 -3 -2 -5 -4 -1\n", "output": "-1 1\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
        "tags": ["Array"], "source": "Custom",
    },
    {
        "title": "Caesar Cipher",
        "description": "<p>Given a string containing only uppercase English letters, shift each letter forward by <strong>k</strong> positions in the alphabet (wrapping around from Z to A). Non-letter characters are not present in the input.</p>",
        "input_description": "<p>The first line contains an integer <strong>k</strong> (0 &lt;= k &lt;= 25), the shift amount. The second line contains a string <strong>s</strong> (1 &lt;= |s| &lt;= 1000) of uppercase letters.</p>",
        "output_description": "<p>Output the encrypted string.</p>",
        "samples": [{"input": "3\nHELLO", "output": "KHOOR"}],
        "hint": "<p>Use ((ch - 'A' + k) % 26) + 'A' to compute the shifted character.</p>",
        "test_cases": [
            {"input": "3\nHELLO\n", "output": "KHOOR\n"},
            {"input": "0\nABC\n", "output": "ABC\n"},
            {"input": "25\nXYZ\n", "output": "WXY\n"},
            {"input": "13\nQDUOJ\n", "output": "DQHBW\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
        "tags": ["String", "Implementation"], "source": "Custom",
    },
    {
        "title": "GCD of Multiple Numbers",
        "description": "<p>Given <strong>n</strong> positive integers, find their greatest common divisor (GCD).</p>",
        "input_description": "<p>The first line contains an integer <strong>n</strong> (2 &lt;= n &lt;= 100). The second line contains <strong>n</strong> integers, each between 1 and 10<sup>9</sup>.</p>",
        "output_description": "<p>Output a single integer: the GCD of all given numbers.</p>",
        "samples": [{"input": "3\n12 18 24", "output": "6"}],
        "hint": "<p>GCD(a, b, c) = GCD(GCD(a, b), c). Use the Euclidean algorithm.</p>",
        "test_cases": [
            {"input": "3\n12 18 24\n", "output": "6\n"},
            {"input": "2\n7 13\n", "output": "1\n"},
            {"input": "4\n100 200 300 400\n", "output": "100\n"},
            {"input": "5\n1 2 3 4 5\n", "output": "1\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Mid",
        "tags": ["Number Theory"], "source": "Custom",
    },
    {
        "title": "Sort and Remove Duplicates",
        "description": "<p>Given <strong>n</strong> integers, sort them in ascending order and remove duplicates. Output the sorted unique values.</p>",
        "input_description": "<p>The first line contains an integer <strong>n</strong> (1 &lt;= n &lt;= 10<sup>5</sup>). The second line contains <strong>n</strong> integers, each between -10<sup>9</sup> and 10<sup>9</sup>.</p>",
        "output_description": "<p>First line: the number of unique values. Second line: the sorted unique values separated by spaces.</p>",
        "samples": [{"input": "8\n3 1 2 3 1 5 2 4", "output": "5\n1 2 3 4 5"}],
        "hint": "<p>Sort first, then iterate to skip duplicates.</p>",
        "test_cases": [
            {"input": "8\n3 1 2 3 1 5 2 4\n", "output": "5\n1 2 3 4 5\n"},
            {"input": "5\n1 1 1 1 1\n", "output": "1\n1\n"},
            {"input": "1\n42\n", "output": "1\n42\n"},
            {"input": "6\n-1 -3 0 -1 2 0\n", "output": "4\n-3 -1 0 2\n"},
        ],
        "time_limit": 2000, "memory_limit": 256, "difficulty": "Mid",
        "tags": ["Sorting"], "source": "Custom",
    },
    {
        "title": "Coin Change (Minimum Coins)",
        "description": "<p>You have coins of denominations: 1, 5, 10, 50, 100, 500. Given an amount <strong>A</strong>, find the minimum number of coins needed to make that amount.</p>",
        "input_description": "<p>A single integer <strong>A</strong> (1 &lt;= A &lt;= 10<sup>9</sup>).</p>",
        "output_description": "<p>Output a single integer: the minimum number of coins.</p>",
        "samples": [{"input": "620", "output": "4"}],
        "hint": "<p>Use the largest denominations first (greedy works for canonical coin systems). 620 = 500 + 100 + 10 + 10 = 4 coins.</p>",
        "test_cases": [
            {"input": "620\n", "output": "4\n"},
            {"input": "1\n", "output": "1\n"},
            {"input": "500\n", "output": "1\n"},
            {"input": "999\n", "output": "15\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Mid",
        "tags": ["Greedy"], "source": "Custom",
    },
    {
        "title": "Climbing Stairs",
        "description": "<p>You are climbing a staircase with <strong>n</strong> steps. Each time you can climb either 1 or 2 steps. How many distinct ways can you reach the top?</p>",
        "input_description": "<p>A single integer <strong>n</strong> (1 &lt;= n &lt;= 50).</p>",
        "output_description": "<p>Output a single integer: the number of distinct ways. The answer fits in a 64-bit signed integer.</p>",
        "samples": [{"input": "2", "output": "2"}, {"input": "3", "output": "3"}],
        "hint": "<p>This is the Fibonacci sequence. ways(n) = ways(n-1) + ways(n-2).</p>",
        "test_cases": [
            {"input": "1\n", "output": "1\n"},
            {"input": "2\n", "output": "2\n"},
            {"input": "10\n", "output": "89\n"},
            {"input": "50\n", "output": "20365011074\n"},
        ],
        "time_limit": 1000, "memory_limit": 256, "difficulty": "Mid",
        "tags": ["Dynamic Programming"], "source": "Custom",
    },
    {
        "title": "Subarray Sum Query",
        "description": "<p>Given an array of <strong>n</strong> integers and <strong>q</strong> queries, each query asks for the sum of elements from index <strong>l</strong> to <strong>r</strong> (1-indexed, inclusive).</p>",
        "input_description": "<p>The first line contains an integer <strong>n</strong> (1 &lt;= n &lt;= 10<sup>5</sup>).</p><p>The second line contains <strong>n</strong> integers.</p><p>The third line contains an integer <strong>q</strong> (1 &lt;= q &lt;= 10<sup>5</sup>).</p><p>Each of the next <strong>q</strong> lines contains two integers <strong>l</strong> and <strong>r</strong> (1 &lt;= l &lt;= r &lt;= n).</p>",
        "output_description": "<p>For each query, output the sum on a separate line.</p>",
        "samples": [{"input": "5\n1 2 3 4 5\n3\n1 3\n2 5\n4 4", "output": "6\n14\n4"}],
        "hint": "<p>Precompute prefix sums: prefix[i] = a[1] + ... + a[i]. Then sum(l,r) = prefix[r] - prefix[l-1].</p>",
        "test_cases": [
            {"input": "5\n1 2 3 4 5\n3\n1 3\n2 5\n4 4\n", "output": "6\n14\n4\n"},
            {"input": "3\n-1 5 -2\n2\n1 3\n2 2\n", "output": "2\n5\n"},
            {"input": "1\n100\n1\n1 1\n", "output": "100\n"},
            {"input": "4\n0 0 0 0\n3\n1 4\n2 3\n1 1\n", "output": "0\n0\n0\n"},
        ],
        "time_limit": 2000, "memory_limit": 256, "difficulty": "Mid",
        "tags": ["Prefix Sum"], "source": "Custom",
    },
]


def login(base_url, username, password):
    """Login to QDUOJ, return (session, csrf_token)."""
    s = requests.Session()
    s.get(f"{base_url}/api/profile")
    csrf = s.cookies.get("csrftoken", "")
    r = s.post(f"{base_url}/api/login", json={"username": username, "password": password},
               headers={"X-CSRFToken": csrf})
    assert r.status_code == 200 and r.json().get("error") is None, f"Login failed: {r.text}"
    csrf = s.cookies.get("csrftoken", csrf)
    print(f"[OK] Logged in as {username}")
    return s, csrf


def build_test_case_score(test_cases):
    """Build test_case_score list with evenly distributed 100 points."""
    if not test_cases:
        return []
    score_each = 100 // len(test_cases)
    scores = []
    for i in range(len(test_cases)):
        s = score_each
        if i == len(test_cases) - 1:
            s = 100 - score_each * (len(test_cases) - 1)
        scores.append({"score": s, "input_name": f"{i+1}.in", "output_name": f"{i+1}.out"})
    return scores


def make_problem_payload(prob, display_id, test_case_id, test_case_score):
    """Build payload dict for POST/PUT /api/admin/problem."""
    return {
        "_id": display_id,
        "title": prob["title"],
        "description": prob["description"],
        "input_description": prob["input_description"],
        "output_description": prob["output_description"],
        "samples": prob.get("samples", []),
        "hint": prob.get("hint", ""),
        "time_limit": prob.get("time_limit", 1000),
        "memory_limit": prob.get("memory_limit", 256),
        "difficulty": prob.get("difficulty", "Low"),
        "tags": prob.get("tags", ["Math"]),
        "source": prob.get("source", "Custom"),
        "test_case_score": test_case_score,
        "test_case_id": test_case_id,
        "rule_type": "ACM",
        "visible": True,
        "languages": ["C", "C++", "Java", "Python3"],
        "template": {},
        "spj": False,
        "spj_language": None,
        "spj_code": None,
        "spj_version": "",
        "spj_compile_ok": False,
        "io_mode": {"input": "input.txt", "output": "output.txt", "io_mode": "Standard IO"},
        "share_submission": False,
        "is_public": False,
    }


def create_problem(s, base_url, csrf, prob, display_id):
    """Create problem via POST, return db id."""
    # Use a placeholder test_case_id first (will be updated after upload)
    placeholder_tc_id = "".join(random.choices("0123456789abcdef", k=32))
    payload = make_problem_payload(prob, display_id, placeholder_tc_id,
                                    build_test_case_score(prob.get("test_cases", [])))
    r = s.post(f"{base_url}/api/admin/problem", json=payload, headers={"X-CSRFToken": csrf})
    data = r.json()
    if data.get("error") is not None:
        print(f"  [FAIL] Create problem: {data['error']}")
        return None
    pid = data["data"]["id"]
    print(f"  [OK] Created problem id={pid}, _id={display_id}")
    return pid


def upload_test_cases(s, base_url, csrf, problem_db_id, test_cases):
    """Upload test cases zip, return test_case_id."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
        with zipfile.ZipFile(tmp_path, "w") as zf:
            for i, tc in enumerate(test_cases, 1):
                zf.writestr(f"{i}.in", tc["input"])
                zf.writestr(f"{i}.out", tc["output"])
    with open(tmp_path, "rb") as f:
        r = s.post(f"{base_url}/api/admin/test_case",
                    files={"file": ("testdata.zip", f, "application/zip")},
                    data={"problem_id": str(problem_db_id), "spj": "false"},
                    headers={"X-CSRFToken": csrf})
    os.unlink(tmp_path)
    data = r.json()
    if data.get("error") is not None:
        print(f"  [FAIL] Upload test cases: {data['error']}")
        return None
    tc_id = data["data"]["id"]
    print(f"  [OK] Uploaded {len(test_cases)} test cases, test_case_id={tc_id}")
    return tc_id


def update_problem(s, base_url, csrf, prob, problem_db_id, display_id, test_case_id, test_case_score):
    """Update problem with real test_case_id via PUT."""
    payload = make_problem_payload(prob, display_id, test_case_id, test_case_score)
    payload["id"] = problem_db_id
    r = s.put(f"{base_url}/api/admin/problem", json=payload, headers={"X-CSRFToken": csrf})
    data = r.json()
    if data.get("error") is not None:
        print(f"  [FAIL] Update problem: {data['error']}")
        return False
    print(f"  [OK] Updated problem with test_case_id={test_case_id}")
    return True


def delete_problem(s, base_url, csrf, problem_db_id):
    """Delete a problem."""
    r = s.delete(f"{base_url}/api/admin/problem?id={problem_db_id}",
                  headers={"X-CSRFToken": csrf})
    return r.json().get("error") is None


def find_custom_problems(s, base_url, csrf):
    """Find all problems with _id starting with 'custom-'."""
    results = []
    page = 1
    while True:
        r = s.get(f"{base_url}/api/admin/problem?limit=50&page={page}",
                   headers={"X-CSRFToken": csrf})
        data = r.json()
        if data.get("error") is not None or not data["data"]["results"]:
            break
        for p in data["data"]["results"]:
            if p["_id"].startswith("custom-"):
                results.append(p)
        page += 1
        if page > 30:  # safety limit
            break
    return results


def main():
    s, csrf = login(OJ_URL, ADMIN_USER, ADMIN_PASS)

    # Clean up any previously created custom problems
    print("\nChecking for existing custom problems...")
    custom = find_custom_problems(s, OJ_URL, csrf)
    if custom:
        print(f"Found {len(custom)} existing custom problems, deleting...")
        for p in custom:
            if delete_problem(s, OJ_URL, csrf, p["id"]):
                print(f"  Deleted id={p['id']} _id={p['_id']}")
    else:
        print("No existing custom problems found.")

    # Import 10 problems
    print(f"\nImporting {len(PROBLEMS)} problems...")
    print("=" * 60)
    stats = {"total": len(PROBLEMS), "success": 0, "failed": 0}
    created_ids = []

    for idx, prob in enumerate(PROBLEMS, 1):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        display_id = f"custom-{suffix}"
        print(f"\n[{idx}/{len(PROBLEMS)}] {prob['title']} (_id={display_id})")

        # Step 1: Create problem (placeholder test_case_id)
        pid = create_problem(s, OJ_URL, csrf, prob, display_id)
        if pid is None:
            stats["failed"] += 1
            continue

        # Step 2: Upload test cases
        tc = prob.get("test_cases", [])
        tc_id = None
        if tc:
            tc_id = upload_test_cases(s, OJ_URL, csrf, pid, tc)
            if tc_id is None:
                stats["failed"] += 1
                # Clean up the orphaned problem
                delete_problem(s, OJ_URL, csrf, pid)
                continue

        # Step 3: Update problem with real test_case_id and score
        tc_score = build_test_case_score(tc) if tc else []
        if tc_id:
            ok = update_problem(s, OJ_URL, csrf, prob, pid, display_id, tc_id, tc_score)
            if not ok:
                stats["failed"] += 1
                delete_problem(s, OJ_URL, csrf, pid)
                continue

        created_ids.append(display_id)
        stats["success"] += 1

    print("\n" + "=" * 60)
    print(f"Result: {stats['success']}/{stats['total']} succeeded, {stats['failed']} failed")
    if created_ids:
        print(f"Created problem IDs: {', '.join(created_ids)}")

    # Verify
    print("\nVerifying...")
    for did in created_ids:
        r = s.get(f"{OJ_URL}/api/problem?keyword={did}", headers={"X-CSRFToken": csrf})
        data = r.json()
        if data["data"]["total"] > 0:
            p = data["data"]["results"][0]
            print(f"  [OK] {p['_id']}: {p['title']} (visible={p['visible']})")
        else:
            print(f"  [FAIL] {did} not found in public API")

    print("\nDone.")


if __name__ == "__main__":
    main()