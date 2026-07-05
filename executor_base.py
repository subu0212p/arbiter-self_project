"""
executor_base.py — the interface every code-execution backend implements.

Read OVERVIEW.md, Milestone 1, before this file.

Why an interface (base class) at all, instead of just writing one function
that runs code? Because HOW you isolate untrusted code from the host
machine is a decision that should be swappable without touching any of the
judging logic built on top of it. Today that's a resource-limited
subprocess (testable anywhere Python runs, see subprocess_executor.py);
tomorrow it could be a Docker container (see docker_executor.py) or
something stronger still - the rest of the system (judge.py, the queue,
the API) never needs to know or care which one is actually running code.
"""

from dataclasses import dataclass


@dataclass
class ExecutionResult:
    verdict: str          # "OK", "TLE", "MLE", "RE", or "CE" - see judge.py
    stdout: str
    stderr: str
    time_taken: float     # seconds
    exit_code: int | None


class Executor:
    """Base interface. Subclasses must implement run()."""

    name = "base"

    def run(self, code: str, language: str, stdin: str,
            time_limit: float, memory_limit_mb: int) -> ExecutionResult:
        raise NotImplementedError
