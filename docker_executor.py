"""
docker_executor.py — sandboxes untrusted code inside a throwaway Docker
container instead of a plain subprocess.

Read OVERVIEW.md, Milestone 8, before this file.

IMPORTANT, stated honestly: this executor requires Docker to be installed
and running, and it could NOT be tested inside the environment this
project was originally built in (no Docker available there). See
CONCEPTS_QA.md, Milestone 8, for why that's a real, deliberate limitation
being surfaced directly rather than hidden. Before relying on this for an
interview demo, verify it yourself on a machine with Docker installed -
e.g. run the __main__ block at the bottom of this file.

Why a container is stronger isolation than SubprocessExecutor's OS
resource limits: a container gets its own filesystem view and its own
process namespace (it can't see or signal host processes), and with
--network none it has no network access at all. A resource-limited
subprocess still shares the host's real filesystem and kernel - stronger
isolation, but also a heavier, slower-to-start execution path, which is
exactly the trade-off worth naming if asked "why have two executors
instead of just using Docker for everything."
"""

import os
import subprocess
import tempfile
import time

from executor_base import Executor, ExecutionResult

IMAGES = {
    "python": "python:3.11-slim",
    "cpp": "gcc:13",
}

RUN_COMMAND = {
    "python": ["python3", "/sandbox/solution.py"],
    "cpp": ["/bin/sh", "-c", "g++ -O2 -o /tmp/a.out /sandbox/solution.cpp && /tmp/a.out"],
}


class DockerExecutor(Executor):
    name = "docker"

    def run(self, code: str, language: str, stdin: str,
            time_limit: float = 2.0, memory_limit_mb: int = 256) -> ExecutionResult:
        if language not in IMAGES:
            raise ValueError(f"unsupported language: {language}")

        with tempfile.TemporaryDirectory() as workdir:
            filename = "solution.py" if language == "python" else "solution.cpp"
            source_path = os.path.join(workdir, filename)
            with open(source_path, "w") as f:
                f.write(code)

            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",                      # no network access at all
                f"--memory={memory_limit_mb}m",             # hard memory cap
                "--memory-swap", f"{memory_limit_mb}m",     # disable swap headroom
                "--cpus", "1",
                "--pids-limit", "20",                        # prevent fork bombs
                "-v", f"{workdir}:/sandbox:ro",               # mount the code read-only
                IMAGES[language],
            ] + RUN_COMMAND[language]

            start = time.time()
            try:
                result = subprocess.run(
                    docker_cmd, input=stdin, capture_output=True,
                    text=True, timeout=time_limit + 5,  # slack for container startup
                )
                elapsed = time.time() - start
            except subprocess.TimeoutExpired:
                elapsed = time.time() - start
                return ExecutionResult(
                    verdict="TLE", stdout="", stderr="",
                    time_taken=elapsed, exit_code=None,
                )

            if result.returncode == 0:
                verdict = "OK"
            elif result.returncode == 137:
                # 137 = 128 + SIGKILL(9) - Docker's own OOM killer exits containers this way
                verdict = "MLE"
            else:
                verdict = "RE"

            return ExecutionResult(
                verdict=verdict, stdout=result.stdout, stderr=result.stderr,
                time_taken=elapsed, exit_code=result.returncode,
            )


if __name__ == "__main__":
    # Manual smoke test - run this file directly on a machine with Docker
    # installed to verify the executor actually works there:
    #   python3 docker_executor.py
    executor = DockerExecutor()
    result = executor.run("print('docker works')", "python", "", 5.0, 256)
    print(result)
    assert result.verdict == "OK"
    assert result.stdout.strip() == "docker works"
    print("DockerExecutor smoke test: PASS")
