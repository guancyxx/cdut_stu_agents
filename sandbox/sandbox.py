"""
Sandbox integration module for CDUT OJ.

Wraps the isolate sandbox CLI for secure code execution.
Designed to run inside the cdut-sandbox Docker container.

Key design decisions:
- Compilation is done OUTSIDE the sandbox (host filesystem)
- Execution is done INSIDE isolate sandbox with resource limits
- Java is compiled externally, only bytecode executed inside
- Uses subprocess for isolate CLI calls
- Meta files are written to /tmp outside the box
"""

from __future__ import annotations

import asyncio
import os
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from enums import Verdict


# ── paths ────────────────────────────────────────────────────────────
ISOLATE_BIN = "/usr/local/bin/isolate"
ISOLATE_BASE = Path("/var/local/lib/isolate")
BOX_RANGE = range(1, 128)  # available box IDs for concurrent submissions


# ── enums / constants ─────────────────────────────────────────────────
class Language(str, Enum):
    C = "c"
    CPP = "cpp"
    PYTHON3 = "python3"
    JAVA = "java"


LANG_META = {
    Language.C: {
        "compile_cmd": lambda src, out: ["gcc", "-O2", "-Wall", "-std=c11", src, "-o", out],
        "run_cmd": lambda bin_path: [f"./{bin_path}"],
        "ext": ".c",
    },
    Language.CPP: {
        "compile_cmd": lambda src, out: ["g++", "-O2", "-Wall", "-std=c++17", src, "-o", out],
        "run_cmd": lambda bin_path: [f"./{bin_path}"],
        "ext": ".cpp",
    },
    Language.PYTHON3: {
        "compile_cmd": None,  # no compilation needed
        "run_cmd": lambda src: ["/usr/bin/python3", src],
        "ext": ".py",
    },
    Language.JAVA: {
        "compile_cmd": lambda src, out_dir: [
            "/usr/lib/jvm/java-21-openjdk-amd64/bin/javac",
            "-J-Xms16m", "-J-Xmx64m",
            "-J-XX:+UseSerialGC", "-J-XX:-UseCompressedClassPointers",
            "-d", out_dir, src,
        ],
        "run_cmd": lambda class_name: [
            "/usr/lib/jvm/java-21-openjdk-amd64/bin/java",
            "-Xms8m", "-Xmx64m",
            "-XX:+UseSerialGC", "-XX:-UseCompressedClassPointers",
            "-Xss256k",
            class_name,
        ],
        "ext": ".java",
    },
}


# ── data structures ───────────────────────────────────────────────────
@dataclass
class CompileResult:
    success: bool
    language: Language
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    artifact_path: Optional[str] = None  # path to compiled binary / class dir


@dataclass
class ExecuteResult:
    verdict: Verdict
    time_sec: float = 0.0
    time_wall_sec: float = 0.0
    max_rss_kb: int = 0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    message: str = ""


class SandboxError(Exception):
    """Sandbox infrastructure error — isolate init failure, missing artifact, etc."""

    def __init__(self, message: str, box_id: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.box_id = box_id


# ── parse meta ────────────────────────────────────────────────────────
def _parse_meta(path: str) -> dict:
    """Parse isolate meta output into a dict."""
    meta = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip()
    except FileNotFoundError:
        pass
    return meta


# ── compile ───────────────────────────────────────────────────────────
async def compile_code(
    code: str,
    language: Language,
    work_dir: Optional[str] = None,
) -> CompileResult:
    """
    Compile source code outside the sandbox.

    Args:
        code: Source code string
        language: Target language
        work_dir: Working directory (auto-created if None)

    Returns:
        CompileResult with success status and artifact path
    """
    info = LANG_META[language]
    if info["compile_cmd"] is None:
        return CompileResult(
            success=True,
            language=language,
            stdout="",
            stderr="",
            exit_code=0,
            artifact_path=None,
        )

    # Use a unique temp dir so concurrent compilations don't collide
    base = Path(work_dir) if work_dir else Path("/tmp/sandbox_compile")
    base.mkdir(parents=True, exist_ok=True)
    job_dir = base / uuid.uuid4().hex[:8]
    job_dir.mkdir(parents=True)

    if language == Language.JAVA:
        # Java requires filename to match public class name
        class_name = _extract_java_class(code) or "Main"
        src_path = job_dir / f"{class_name}.java"
        src_path.write_text(code, encoding="utf-8")
        cmd = info["compile_cmd"](str(src_path), str(job_dir))
        artifact = str(job_dir)
    else:
        src_path = job_dir / f"solution{info['ext']}"
        src_path.write_text(code, encoding="utf-8")
        out_path = job_dir / "solution"
        cmd = info["compile_cmd"](str(src_path), str(out_path))
        artifact = str(out_path)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=30.0
        )
        exit_code = proc.returncode or 0
    except asyncio.TimeoutError:
        proc.kill()
        return CompileResult(
            success=False,
            language=language,
            stdout="",
            stderr="Compilation timed out (30s)",
            exit_code=-1,
        )

    stdout_s = stdout.decode("utf-8", errors="replace")[:4096]
    stderr_s = stderr.decode("utf-8", errors="replace")[:4096]

    if exit_code != 0:
        return CompileResult(
            success=False,
            language=language,
            stdout=stdout_s,
            stderr=stderr_s,
            exit_code=exit_code,
        )

    return CompileResult(
        success=True,
        language=language,
        stdout=stdout_s,
        stderr=stderr_s,
        exit_code=0,
        artifact_path=artifact,
    )


# ── execute ───────────────────────────────────────────────────────────
async def execute(
    artifact_path: str,
    language: Language,
    input_data: str = "",
    time_limit: float = 2.0,
    memory_limit_kb: int = 262144,
    processes_limit: int = 100,
    box_id: Optional[int] = None,
) -> ExecuteResult:
    """
    Execute compiled artifact inside an isolate sandbox.

    Args:
        artifact_path: Path to compiled binary or source file (Python)
        input_data: stdin content
        time_limit: CPU time limit in seconds
        memory_limit_kb: Memory limit in KB
        processes_limit: Max processes/threads
        box_id: Specific box ID (auto-allocated if None)

    Returns:
        ExecuteResult with verdict and resource usage
    """

    # Allocate a box ID
    if box_id is None:
        box_id = _allocate_box()
    else:
        box_id = int(box_id)

    info = LANG_META[language]
    box_dir = ISOLATE_BASE / str(box_id)
    meta_path = f"/tmp/meta_{box_id}"

    # ── init sandbox ──
    try:
        proc = await asyncio.create_subprocess_exec(
            ISOLATE_BIN, "--init", "-b", str(box_id),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=5.0)
        if proc.returncode != 0:
            raise SandboxError(f"isolate --init failed for box {box_id}", box_id)
    except asyncio.TimeoutError:
        raise SandboxError(f"isolate --init timed out for box {box_id}", box_id)

    try:
        # Copy artifact into box
        if language == Language.PYTHON3:
            # artifact_path is the .py file, just copy it
            script_name = os.path.basename(artifact_path)
            dest = box_dir / "box" / script_name
            _safe_copy(artifact_path, str(dest))
            run_args = info["run_cmd"](script_name)
        elif language == Language.JAVA:
            # artifact_path is the directory with .class files
            # Extract class name from compile artifact (main class file)
            class_files = list(Path(artifact_path).glob("*.class"))
            if not class_files:
                raise SandboxError("No .class files in java artifact", box_id)
            class_name = class_files[0].stem  # "Hello" from Hello.class
            for f in class_files:
                _safe_copy(str(f), str(box_dir / "box" / f.name))
            run_args = info["run_cmd"](class_name)
        else:
            # C / C++ binary
            dest = box_dir / "box" / "solution"
            _safe_copy(artifact_path, str(dest))
            run_args = info["run_cmd"]("solution")

        # Write stdin
        stdin_path = box_dir / "box" / "stdin.txt"
        stdin_path.write_text(input_data, encoding="utf-8")

        # ── execute ──
        cmd = [
            ISOLATE_BIN, "--run",
            "-b", str(box_id),
            f"--time={time_limit}",
            f"--mem={memory_limit_kb}",
            f"--processes={processes_limit}",
            "--stdin", "stdin.txt",
            "--stdout", "stdout.txt",
            "--stderr", "stderr.txt",
            f"--meta={meta_path}",
            "--dir=/usr",
            "--dir=/etc",
            "--dir=/tmp",
            "--dir=/lib",
            "--dir=/lib64",
            "--dir=/proc",
            "--",
        ] + run_args

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=time_limit * 2 + 5.0)

        # Read outputs
        stdout = ""
        stderr = ""
        try:
            stdout = (box_dir / "box" / "stdout.txt").read_text(
                encoding="utf-8", errors="replace"
            )[:65536]
        except Exception:
            pass
        try:
            stderr = (box_dir / "box" / "stderr.txt").read_text(
                encoding="utf-8", errors="replace"
            )[:4096]
        except Exception:
            pass

        # Parse meta
        meta = _parse_meta(meta_path)
        time_sec = float(meta.get("time", 0))
        time_wall_sec = float(meta.get("time-wall", 0))
        max_rss_kb = int(meta.get("max-rss", 0))
        exit_code = int(meta.get("exitcode", 0))
        message = meta.get("message", "")
        status = meta.get("status", "")
        killed = int(meta.get("killed", 0))

        # ── determine verdict ──
        verdict = _determine_verdict(
            status, message, exit_code, killed,
            time_sec, time_limit,
            max_rss_kb, memory_limit_kb,
        )

    except asyncio.TimeoutError:
        verdict = Verdict.TLE
        time_sec = time_limit
        time_wall_sec = time_limit
        exit_code = -1
        message = "Sandbox execution timed out"
        meta = {}

    finally:
        # Always cleanup
        try:
            cleanup_proc = await asyncio.create_subprocess_exec(
                ISOLATE_BIN, "--cleanup", "-b", str(box_id),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(cleanup_proc.communicate(), timeout=5.0)
        except Exception:
            pass

    return ExecuteResult(
        verdict=verdict,
        time_sec=time_sec,
        time_wall_sec=time_wall_sec,
        max_rss_kb=max_rss_kb,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        message=message,
    )


# ── verdict determination ─────────────────────────────────────────────
def _determine_verdict(
    status: str,
    message: str,
    exit_code: int,
    killed: int,
    time_sec: float,
    time_limit: float,
    max_rss_kb: int,
    memory_limit_kb: int,
) -> Verdict:
    """
    Map isolate status/meta to a CDUT OJ verdict.

    Order matters: TLE/MLE > RE > SE > AC (AC only if no error)
    """
    # Time limit exceeded
    if status == "TO" or message == "Time limit exceeded" or killed:
        if killed:
            return Verdict.TLE
        return Verdict.TLE

    # Memory limit exceeded — rlimit mode: process killed by OOM or exitcode=SIGKILL
    # Note: without --cg, isolate uses rlimit, no clean MLE message
    if max_rss_kb >= memory_limit_kb * 0.95:
        return Verdict.MLE
    if exit_code == 137 or exit_code == -9:  # SIGKILL (often OOM)
        return Verdict.MLE
    # rlimit mode: small memory limit causes program to exit immediately with non-zero
    if memory_limit_kb < 65536 and exit_code != 0 and time_sec < 0.01:
        return Verdict.MLE

    # Runtime error — non-zero exit, signals (SIGSEGV/SIGBUS/SIGFPE etc.)
    if exit_code != 0 or status == "RE":
        return Verdict.RE
    # Sandbox-detected fatal signal (SEGFAULT, etc.) — treat as RE
    if status == "SG":
        return Verdict.RE

    # Accepted — only if no error condition fired
    return Verdict.AC


# ── helpers ───────────────────────────────────────────────────────────
def _extract_java_class(code: str) -> Optional[str]:
    """Extract public class name from Java source."""
    m = re.search(r'public\s+class\s+(\w+)', code)
    return m.group(1) if m else None


def _allocate_box() -> int:
    """Pick a free box ID. Simple round-robin; a proper pool is better for production."""
    # Use PID-based allocation for now — simple and collision-free within one process
    pid = os.getpid()
    return BOX_RANGE[pid % len(BOX_RANGE)]


def _safe_copy(src: str, dst: str) -> None:
    """Copy file with proper permissions for isolate."""
    import shutil
    shutil.copy2(src, dst)
    os.chmod(dst, 0o755)  # isolate requires executable permission in box


# ── convenience: full compile+run pipeline ────────────────────────────
async def run_code(
    code: str,
    language: Language,
    input_data: str = "",
    time_limit: float = 2.0,
    memory_limit_kb: int = 262144,
) -> tuple[CompileResult, Optional[ExecuteResult]]:
    """
    Compile and execute code in one call.

    Returns (compile_result, execute_result).
    execute_result is None if compilation failed.
    """
    compile_result = await compile_code(code, language)

    if not compile_result.success:
        return compile_result, None

    if language == Language.PYTHON3:
        # artifact is the source file itself
        artifact = _write_temp(code, language)
    else:
        artifact = compile_result.artifact_path

    if artifact is None:
        return compile_result, ExecuteResult(
            verdict=Verdict.SE,
            message="No artifact produced after compilation",
        )

    execute_result = await execute(
        artifact_path=artifact,
        language=language,
        input_data=input_data,
        time_limit=time_limit,
        memory_limit_kb=memory_limit_kb,
    )

    return compile_result, execute_result


def _write_temp(code: str, language: Language) -> str:
    """Write code to a temp file, return path."""
    path = f"/tmp/sandbox_run_{uuid.uuid4().hex[:8]}{LANG_META[language]['ext']}"
    Path(path).write_text(code, encoding="utf-8")
    return path
