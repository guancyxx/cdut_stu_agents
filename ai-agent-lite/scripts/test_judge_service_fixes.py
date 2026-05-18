"""Lightweight regression checks for judge_service helper logic."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.judge_service import (  # noqa: E402
    JAVA_MEMORY_FLOOR_KB,
    _effective_memory_limit_kb,
    _sanitize_submission_code,
)


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected={expected!r}, actual={actual!r}")


def test_java_memory_floor() -> None:
    assert_equal(
        _effective_memory_limit_kb("java", 512 * 1024),
        JAVA_MEMORY_FLOOR_KB,
        "java should apply minimum memory floor",
    )
    assert_equal(
        _effective_memory_limit_kb("java", 2 * 1024 * 1024),
        2 * 1024 * 1024,
        "java should keep larger configured memory",
    )
    assert_equal(
        _effective_memory_limit_kb("python3", 256 * 1024),
        256 * 1024,
        "non-java language should keep configured memory",
    )


def test_python_marker_sanitization() -> None:
    marker_code = """//PREPEND BEGIN
# helper
//PREPEND END

//TEMPLATE BEGIN
def solve():
    print('ok')
//TEMPLATE END

//APPEND BEGIN
if __name__ == '__main__':
    solve()
//APPEND END
"""
    sanitized = _sanitize_submission_code(marker_code, "python3")
    assert "//PREPEND BEGIN" not in sanitized
    assert "//TEMPLATE BEGIN" not in sanitized
    assert "def solve()" in sanitized
    assert "if __name__ == '__main__':" in sanitized


def test_java_marker_sanitization() -> None:
    marker_code = """//PREPEND BEGIN
import java.util.*;
//PREPEND END

//TEMPLATE BEGIN
public class Main {
    public static void main(String[] args) {
        System.out.print(\"ok\");
    }
}
//TEMPLATE END

//APPEND BEGIN
//APPEND END
"""
    sanitized = _sanitize_submission_code(marker_code, "java")
    assert "//PREPEND BEGIN" not in sanitized
    assert "public class Main" in sanitized


def test_no_marker_passthrough() -> None:
    plain = "print('plain')\n"
    assert_equal(
        _sanitize_submission_code(plain, "python3"),
        plain,
        "plain code should pass through unchanged",
    )


if __name__ == "__main__":
    test_java_memory_floor()
    test_python_marker_sanitization()
    test_java_marker_sanitization()
    test_no_marker_passthrough()
    print("OK: judge_service fix tests passed")
