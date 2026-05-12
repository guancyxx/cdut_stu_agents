"""
Unit tests for sandbox verdict coverage.

Tests every OJ verdict via the sandbox API:
  AC, WA, TLE, MLE, RE, CE

Run from the sandbox container: python3 /workspace/test_verdicts.py
"""

import subprocess
import json
import sys

BASE_URL = "http://localhost:8899"


def run(code: str, language: str, input_data: str = "", time_limit: float = 2.0, memory_limit_kb: int = 262144) -> dict:
    body = json.dumps({
        "code": code,
        "language": language,
        "input_data": input_data,
        "time_limit": time_limit,
        "memory_limit_kb": memory_limit_kb,
    })
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{BASE_URL}/run",
         "-H", "Content-Type: application/json",
         "-d", body],
        capture_output=True, text=True, timeout=30,
    )
    return json.loads(result.stdout)


passed = 0
failed = 0


def test(name: str, code: str, language: str, input_data: str, expected_verdict: str,
         time_limit: float = 2.0, memory_limit_kb: int = 262144) -> None:
    global passed, failed
    result = run(code, language, input_data, time_limit, memory_limit_kb)
    actual = result.get("verdict", "?")
    status = "PASS" if actual == expected_verdict else "FAIL"
    if status == "PASS":
        passed += 1
    else:
        failed += 1
    print(f"[{status}] {name}: expected={expected_verdict} actual={actual} time={result.get('time_sec',0):.3f}s")
    if status == "FAIL" and actual != expected_verdict:
        print(f"       compile_error={result.get('compile_stderr','')[:120]}")
        print(f"       stdout={result.get('stdout','')[:80]}")
        print(f"       message={result.get('message','')}")


print("=" * 60)
print("CDUT OJ — Sandbox Verdict Coverage Tests")
print("=" * 60)

# ══════════════════════════════════════════════════════════════════════
# AC: Correct A+B program
# ══════════════════════════════════════════════════════════════════════
test(
    "AC — C A+B",
    '#include <stdio.h>\nint main() { int a,b; scanf("%d%d",&a,&b); printf("%d",a+b); return 0; }',
    "c", "3 5", "AC",
)

test(
    "AC — Python3 A+B",
    'a,b=map(int,input().split())\nprint(a+b)',
    "python3", "7 9", "AC",
)

test(
    "AC — C++ Hello",
    '#include <iostream>\nint main() { std::cout << "OK"; return 0; }',
    "cpp", "", "AC",
)

test(
    "AC — Java Hello",
    'public class Main { public static void main(String[] args) { System.out.print("OK"); } }',
    "java", "", "AC",
    time_limit=5.0, memory_limit_kb=1048576,
)

# ══════════════════════════════════════════════════════════════════════
# WA: Program runs but produces wrong output
# ══════════════════════════════════════════════════════════════════════
test(
    "WA — wrong sum",
    '#include <stdio.h>\nint main() { int a,b; scanf("%d%d",&a,&b); printf("%d",a-b); return 0; }',
    "c", "3 5", "AC",  # sandbox returns AC; WA detection is in judge_service
)
# Note: WA is determined by the judge_service comparing stdout vs expected,
# not by the sandbox itself. The sandbox correctly reports AC here.
# This is verified by the end-to-end /api/submit test with an actual problem.

# ══════════════════════════════════════════════════════════════════════
# TLE: Time Limit Exceeded (infinite loop)
# ══════════════════════════════════════════════════════════════════════
test(
    "TLE — infinite loop",
    'int main() { while(1) {} }',
    "c", "", "TLE",
    time_limit=0.5,
)

test(
    "TLE — Python3 infinite loop",
    'while True: pass',
    "python3", "", "TLE",
    time_limit=0.5,
)

# ══════════════════════════════════════════════════════════════════════
# RE: Runtime Error (division by zero)
# ══════════════════════════════════════════════════════════════════════
test(
    "RE — division by zero (runtime)",
    '#include <stdio.h>\nint main() { int a,b; scanf("%d%d",&a,&b); printf("%d",a/b); return 0; }',
    "c", "5 0", "RE",
    time_limit=1.0,
)

test(
    "RE — Python3 exception",
    'raise Exception("test error")',
    "python3", "", "RE",
    time_limit=1.0,
)

test(
    "RE — segfault",
    '#include <stdio.h>\nint main() { int *p=0; *p=42; return 0; }',
    "c", "", "RE",
    time_limit=1.0,
)

# ══════════════════════════════════════════════════════════════════════
# CE: Compilation Error (invalid syntax)
# ══════════════════════════════════════════════════════════════════════
test(
    "CE — missing semicolon",
    '#include <stdio.h>\nint main() { return 0 }',
    "c", "", "CE",
)

test(
    "CE — Java syntax error",
    'public class Main { public static void main(String[] args) { System.out.print(',
    "java", "", "CE",
    time_limit=5.0, memory_limit_kb=1048576,
)

# ══════════════════════════════════════════════════════════════════════
# MLE: Memory Limit Exceeded
# ══════════════════════════════════════════════════════════════════════
test(
    "MLE — large allocation beyond 8MB limit",
    '#include <stdlib.h>\n#include <string.h>\nint main() { '
    'size_t sz=16*1024*1024; char *p=malloc(sz); '
    'if(!p) return 1; for(size_t i=0;i<sz;i+=4096)p[i]=1; return 0; }',
    "c", "", "MLE",
    time_limit=2.0, memory_limit_kb=8192,
)

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed+failed} total")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
