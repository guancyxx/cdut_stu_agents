"""FPS XML and Hydro ZIP parsers for batch problem import.

Parses problem package files into a normalized list of problem dicts
that can be fed into ProblemService.create_problem().

Output format per problem:
{
    "title": str,
    "description": str,
    "input_description": str,
    "output_description": str,
    "samples": [{"input": str, "output": str}],
    "hint": str,
    "source": str,
    "difficulty": str,       # "Low" | "Mid" | "High"
    "tags": [str],
    "time_limit": int,       # ms
    "memory_limit": int,     # MB
    "test_cases": [{"input": str, "output": str, "score": int}],
    "languages": [str],
}
"""

import logging
import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

logger = logging.getLogger("ai-agent-lite.problem_import")


# ---------------------------------------------------------------------------
# Difficulty mapping
# ---------------------------------------------------------------------------

DIFFICULTY_MAP = {
    "1": "Low", "2": "Low",
    "3": "Mid", "4": "Mid",
    "5": "High",
    "low": "Low", "mid": "Mid", "high": "High",
    "easy": "Low", "medium": "Mid", "hard": "High",
    "简单": "Low", "中等": "Mid", "困难": "High",
}

HYDRO_DIFFICULTY_MAP = {
    1: "Low", 2: "Low",
    3: "Mid", 4: "Mid",
    5: "High", 6: "High", 7: "High",
}


# ---------------------------------------------------------------------------
# FPS XML parser
# ---------------------------------------------------------------------------

def parse_fps_xml(xml_path: Path | str) -> list[dict]:
    """Parse an FPS (Free Problem Set) XML file into problem dicts.

    FPS format: root <fps> → <item> per problem.
    Each <item> has: <title>, <description>, <input>, <output>,
    <sample_input>, <sample_output>, <hint>, <source>,
    <time_limit>, <memory_limit>, <difficulty>, <tag>,
    <test_input>, <test_output>.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    problems = []
    for item in root.iter("item"):
        try:
            prob = _parse_fps_item(item)
            if prob:
                problems.append(prob)
        except Exception as e:
            logger.warning("Failed to parse FPS item: %s", e)
            continue

    logger.info("Parsed %d problems from FPS XML", len(problems))
    return problems


def _parse_fps_item(item: ET.Element) -> dict | None:
    """Parse a single <item> element from FPS XML."""
    title = _elem_text(item, "title", "").strip()
    if not title:
        return None

    description = _elem_text(item, "description", "")
    input_desc = _elem_text(item, "input", "")
    output_desc = _elem_text(item, "output", "")
    hint = _elem_text(item, "hint", "")
    source = _elem_text(item, "source", "")

    # Time/memory limits
    time_limit = int(_elem_text(item, "time_limit", "1000") or "1000")
    memory_limit = int(_elem_text(item, "memory_limit", "256") or "256")

    # FPS sometimes stores limits with unit suffix like "1000MS" or "256MB"
    time_limit = _strip_unit(time_limit, "MS")
    memory_limit = _strip_unit(memory_limit, "MB")

    # Difficulty
    diff_raw = _elem_text(item, "difficulty", "Low")
    difficulty = DIFFICULTY_MAP.get(str(diff_raw).strip(), "Low")

    # Tags: <tag> elements, can be multiple
    tags = []
    for tag_elem in item.iter("tag"):
        tag_text = (tag_elem.text or "").strip()
        if tag_text:
            tags.append(tag_text)

    # Samples: <sample_input> / <sample_output>
    samples = []
    sample_inputs = [e.text or "" for e in item.iter("sample_input")]
    sample_outputs = [e.text or "" for e in item.iter("sample_output")]
    for si, so in zip(sample_inputs, sample_outputs):
        samples.append({"input": si.strip(), "output": so.strip()})

    # Test cases: <test_input> / <test_output>
    test_cases = []
    test_inputs = [e.text or "" for e in item.iter("test_input")]
    test_outputs = [e.text or "" for e in item.iter("test_output")]
    for ti, to in zip(test_inputs, test_outputs):
        test_cases.append({"input": ti, "output": to})

    # If no test cases but has samples, use samples as test cases
    if not test_cases and samples:
        test_cases = [{"input": s["input"], "output": s["output"]} for s in samples]

    return {
        "title": title,
        "description": description,
        "input_description": input_desc,
        "output_description": output_desc,
        "samples": samples,
        "hint": hint,
        "source": source,
        "difficulty": difficulty,
        "tags": tags,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "test_cases": test_cases,
        "languages": ["C", "C++", "Java", "Python3"],
    }


# ---------------------------------------------------------------------------
# Hydro ZIP parser
# ---------------------------------------------------------------------------

def parse_hydro_zip(zip_path: Path | str) -> list[dict]:
    """Parse a Hydro OJ export ZIP into problem dicts.

    Hydro ZIP structure:
        problem.yaml  — per-problem metadata
        problem.md    — description in Markdown
       testdata/      — test case files (1.in, 1.out, ...)

    Multiple problems: each in a subdirectory.
    """
    problems = []
    with tempfile.TemporaryDirectory(prefix="hydro_import_") as tmp_dir:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        tmp = Path(tmp_dir)

        # Find all problem directories (those containing problem.yaml)
        yaml_files = list(tmp.rglob("problem.yaml"))
        if not yaml_files:
            # Maybe single-problem ZIP: yaml is at root
            yaml_files = list(tmp.glob("problem.yaml"))

        for yaml_path in yaml_files:
            try:
                prob = _parse_hydro_problem(yaml_path)
                if prob:
                    problems.append(prob)
            except Exception as e:
                logger.warning("Failed to parse Hydro problem at %s: %s", yaml_path, e)

    logger.info("Parsed %d problems from Hydro ZIP", len(problems))
    return problems


def _parse_hydro_problem(yaml_path: Path) -> dict | None:
    """Parse a single Hydro problem directory."""
    import yaml  # lazy import — only needed for Hydro

    prob_dir = yaml_path.parent

    with open(yaml_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f) or {}

    title = meta.get("title", "").strip()
    if not title:
        # Fallback: use directory name
        title = prob_dir.name

    # Description from problem.md
    description = ""
    md_path = prob_dir / "problem.md"
    if md_path.exists():
        description = md_path.read_text(encoding="utf-8")

    # Limits
    time_limit = meta.get("time", 1000)
    memory_limit = meta.get("memory", 256)

    # Hydro time is in ms, memory in MB — already correct
    if isinstance(time_limit, (list, tuple)):
        time_limit = time_limit[0] if time_limit else 1000
    if isinstance(memory_limit, (list, tuple)):
        memory_limit = memory_limit[0] if memory_limit else 256
    time_limit = int(time_limit)
    memory_limit = int(memory_limit)

    # Difficulty
    diff_raw = meta.get("difficulty", 0)
    difficulty = HYDRO_DIFFICULTY_MAP.get(int(diff_raw), "Low") if diff_raw else "Low"

    # Tags
    tags = meta.get("tag", [])
    if isinstance(tags, str):
        tags = [tags]

    # Hint
    hint = meta.get("hint", "")
    if isinstance(hint, list):
        hint = "\n".join(str(h) for h in hint)

    # Source / origin
    source = meta.get("source", "") or meta.get("origin", "")

    # Test cases from testdata/ directory
    test_cases = []
    testdata_dir = prob_dir / "testdata"
    if testdata_dir.is_dir():
        test_cases = _scan_testdata_dir(testdata_dir)

    # Samples: Hydro stores them in meta or as separate sample files
    samples = meta.get("samples", [])
    if isinstance(samples, list):
        normalized_samples = []
        for s in samples:
            if isinstance(s, dict):
                normalized_samples.append({
                    "input": s.get("input", ""),
                    "output": s.get("output", ""),
                })
        samples = normalized_samples
    else:
        samples = []

    # If no samples from meta, try to read from problem.md sections
    if not samples and description:
        samples = _extract_samples_from_md(description)

    # If no test cases but has samples, use samples as test cases
    if not test_cases and samples:
        test_cases = [{"input": s["input"], "output": s["output"]} for s in samples]

    return {
        "title": title,
        "description": description,
        "input_description": meta.get("input", "") or _extract_section_md(description, "输入格式"),
        "output_description": meta.get("output", "") or _extract_section_md(description, "输出格式"),
        "samples": samples,
        "hint": hint,
        "source": source,
        "difficulty": difficulty,
        "tags": tags,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "test_cases": test_cases,
        "languages": ["C", "C++", "Java", "Python3"],
    }


def _scan_testdata_dir(testdata_dir: Path) -> list[dict]:
    """Scan testdata/ for .in/.out file pairs."""
    test_cases = []
    in_files = sorted(testdata_dir.glob("*.in"))

    for in_file in in_files:
        out_file = in_file.with_suffix(".out")
        if not out_file.exists():
            continue

        input_text = in_file.read_text(encoding="utf-8", errors="replace")
        output_text = out_file.read_text(encoding="utf-8", errors="replace")
        test_cases.append({"input": input_text, "output": output_text})

    return test_cases


def _extract_samples_from_md(md_text: str) -> list[dict]:
    """Try to extract sample input/output from Markdown problem description."""
    samples = []
    # Simple heuristic: look for ```input / ```output code blocks
    import re
    input_blocks = re.findall(r'```input\s*\n(.*?)```', md_text, re.DOTALL)
    output_blocks = re.findall(r'```output\s*\n(.*?)```', md_text, re.DOTALL)

    for inp, out in zip(input_blocks, output_blocks):
        samples.append({"input": inp.strip(), "output": out.strip()})

    return samples


def _extract_section_md(md_text: str, section_title: str) -> str:
    """Extract a section from Markdown by its heading."""
    import re
    pattern = rf'#+\s*{re.escape(section_title)}\s*\n(.*?)(?=\n#|\Z)'
    match = re.search(pattern, md_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _elem_text(parent: ET.Element, tag: str, default: str = "") -> str:
    """Get text content of a child element, or default."""
    elem = parent.find(tag)
    if elem is not None and elem.text:
        return elem.text
    return default


def _strip_unit(value: int, suffix: str) -> int:
    """Strip unit suffix if present as part of the numeric value (already parsed)."""
    # This handles cases where the value was parsed as int but the original
    # had a suffix. Since we already parsed as int, this is a no-op unless
    # the value is unreasonably large (e.g. time in seconds instead of ms).
    if suffix == "MB" and value > 10240:
        # Likely in KB, convert to MB
        return value // 1024
    if suffix == "MS" and value > 100000:
        # Likely in seconds, convert to ms
        return value * 1000
    return value


def detect_format(filename: str) -> str:
    """Detect import format from filename extension.

    Returns: "fps" or "hydro"
    """
    lower = filename.lower()
    if lower.endswith(".xml"):
        return "fps"
    if lower.endswith(".zip"):
        return "hydro"
    raise ValueError(f"不支持的文件格式: {filename}，仅支持 .xml (FPS) 和 .zip (Hydro)")
