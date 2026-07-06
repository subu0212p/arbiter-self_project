"""
subprocess_executor.py — sandboxes untrusted code using OS-level resource
limits on a plain subprocess, instead of a container.

Read OVERVIEW.md, Milestone 1, before this file.

This is the executor we can fully test in any plain Python environment
with no Docker required, and it's a real, legitimate technique - not a
toy. Smaller online judges and university auto-graders run exactly this
way. It's weaker isolation than a container (the code still shares the
host's actual filesystem and kernel), which is exactly why
docker_executor.py exists alongside it - see CONCEPTS_QA.md for that
trade-off, spelled out honestly.

Cross-platform note (see CONCEPTS_QA.md, Milestone 1, "What changes on
Windows?"): resource.setrlimit and RLIMIT_CPU/RLIMIT_AS/RLIMIT_NPROC are
POSIX-only - they don't exist on Windows at all. Rather than hide that,
this file has two code paths: the original POSIX one below (unchanged,
tested), and a Windows fallback that approximates the same protections
using subprocess timeouts + a psutil-based memory watchdog thread. This
split is a real, honest, interview-worthy design decision, not a hack.
"""

import os
import subprocess
import sys
import tempfile
import threading
import time

from executor_base import Executor, ExecutionResult

IS_POSIX = os.name == "posix"

if IS_POSIX:
    import resource

    def _make_preexec_fn(cpu_seconds: int, memory_mb: int):
        """Returns a function that runs INSIDE the child process, after
        fork() but before exec() - this is the only point at which
        resource.setrlimit can constrain that specific child process
        without affecting our own (the judge server's) process."""
        def limit_resources():
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            mem_bytes = memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_NPROC, (20, 20))
        return limit_resources
else:
    try:
        import psutil
    except ImportError:
        psutil = None  # memory-limit enforcement degrades gracefully (see _run_windows)


class SubprocessExecutor(Executor):
    name = "subprocess"

    def _compile_cpp(self, source_path: str, workdir: str):
        binary_name = "a.out" if IS_POSIX else "a.exe"
        binary_path = os.path.join(workdir, binary_name)
        try:
            result = subprocess.run(
                ["g++", "-O2", "-o", binary_path, source_path],
                capture_output=True, text=True, timeout=10,
            )
        except FileNotFoundError:
            # g++ isn't installed / isn't on PATH. Without this catch, this
            # exception would propagate all the way up through judge.py
            # into the worker thread in queue_worker.py - if that thread
            # had nothing wrapping it, it would die silently and the
            # submission would be stuck showing "Judging..." forever. We
            # surface it as a normal CE instead, with a message that
            # actually says what's wrong (see README's "C++ submissions"
            # note for how to install a compiler on Windows).
            return False, (
                "g++ not found. A C++ compiler isn't installed or isn't on "
                "PATH - see README.md's 'C++ submissions on Windows' note. "
                "Python submissions don't need this."
            ), binary_path
        return result.returncode == 0, result.stderr, binary_path

    def _run_posix(self, run_cmd, stdin, time_limit, memory_limit_mb):
        cpu_limit_seconds = max(1, int(time_limit) + 1)
        start = time.time()
        try:
            result = subprocess.run(
                run_cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=time_limit,
                preexec_fn=_make_preexec_fn(cpu_limit_seconds, memory_limit_mb),
            )
            elapsed = time.time() - start
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            return ExecutionResult(
                verdict="TLE", stdout="", stderr="",
                time_taken=elapsed, exit_code=None,
            )

        # Distinguishing "out of memory" from "any other crash" is a
        # genuine limitation of ulimit-based sandboxing - the OS doesn't
        # hand back one clean unambiguous signal for "this was killed for
        # exceeding RLIMIT_AS" the way a container runtime's OOM killer
        # does. Python surfaces a hit RLIMIT_AS as a catchable MemoryError
        # (visible in stderr); C++ typically surfaces it as std::bad_alloc.
        # We use that as a heuristic - see CONCEPTS_QA.md, Milestone 1, for
        # why this is a real, named trade-off rather than a hidden
        # inaccuracy.
        if result.returncode == 0:
            verdict = "OK"
        elif "MemoryError" in result.stderr or "bad_alloc" in result.stderr:
            verdict = "MLE"
        else:
            verdict = "RE"

        return ExecutionResult(
            verdict=verdict,
            stdout=result.stdout,
            stderr=result.stderr,
            time_taken=elapsed,
            exit_code=result.returncode,
        )

    def _run_windows(self, run_cmd, stdin, time_limit, memory_limit_mb):
        """Windows has no resource.setrlimit equivalent, so we approximate
        the same three protections a different way:
          - wall-clock timeout (subprocess already supports this cross-
            platform) still catches an infinite loop -> TLE.
          - a background thread polls the child's RSS via psutil and kills
            it the moment it crosses memory_limit_mb -> MLE. This is
            polling-based (checked every 20ms), not an instant OS-level
            hard cap the way RLIMIT_AS is, so a process that allocates a
            huge amount of memory in a single instant could in principle
            spike past the limit between polls - a real, named difference
            from the POSIX path, worth mentioning if asked.
          - process-count capping (RLIMIT_NPROC, the fork-bomb defense) has
            no practical equivalent here and is simply NOT enforced on
            this path. A real deployment of this project would run on
            Linux (or inside Docker, itself Linux-based regardless of
            host OS) where the POSIX path above applies in full.
        """
        start = time.time()
        proc = subprocess.Popen(
            run_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        mle_triggered = threading.Event()

        def watch_memory():
            if psutil is None:
                return  # no psutil installed: timeout-only protection, degrades gracefully
            mem_limit_bytes = memory_limit_mb * 1024 * 1024
            try:
                ps_proc = psutil.Process(proc.pid)
            except psutil.NoSuchProcess:
                return
            while proc.poll() is None:
                try:
                    rss = ps_proc.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return
                if rss > mem_limit_bytes:
                    mle_triggered.set()
                    proc.kill()
                    return
                time.sleep(0.02)

        watcher = threading.Thread(target=watch_memory, daemon=True)
        watcher.start()

        try:
            stdout, stderr = proc.communicate(input=stdin, timeout=time_limit)
            elapsed = time.time() - start
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            elapsed = time.time() - start
            return ExecutionResult(
                verdict="TLE", stdout="", stderr="",
                time_taken=elapsed, exit_code=None,
            )

        watcher.join(timeout=0.5)

        if mle_triggered.is_set():
            return ExecutionResult(
                verdict="MLE", stdout="", stderr=stderr,
                time_taken=elapsed, exit_code=proc.returncode,
            )

        if proc.returncode == 0:
            verdict = "OK"
        elif "MemoryError" in stderr or "bad_alloc" in stderr:
            verdict = "MLE"
        else:
            verdict = "RE"

        return ExecutionResult(
            verdict=verdict,
            stdout=stdout,
            stderr=stderr,
            time_taken=elapsed,
            exit_code=proc.returncode,
        )

    def run(self, code: str, language: str, stdin: str,
            time_limit: float = 2.0, memory_limit_mb: int = 256) -> ExecutionResult:
        with tempfile.TemporaryDirectory() as workdir:
            if language == "python":
                source_path = os.path.join(workdir, "solution.py")
                with open(source_path, "w") as f:
                    f.write(code)
                # sys.executable, not a hardcoded "python3": on Windows the
                # command is just "python" (no "python3" alias exists) -
                # sys.executable is always the interpreter actually running
                # this file, on every platform.
                run_cmd = [sys.executable, source_path]

            elif language == "cpp":
                source_path = os.path.join(workdir, "solution.cpp")
                with open(source_path, "w") as f:
                    f.write(code)
                ok, compile_error, binary_path = self._compile_cpp(source_path, workdir)
                if not ok:
                    return ExecutionResult(
                        verdict="CE", stdout="", stderr=compile_error,
                        time_taken=0.0, exit_code=None,
                    )
                run_cmd = [binary_path]

            else:
                raise ValueError(f"unsupported language: {language}")

            if IS_POSIX:
                return self._run_posix(run_cmd, stdin, time_limit, memory_limit_mb)
            else:
                return self._run_windows(run_cmd, stdin, time_limit, memory_limit_mb)
