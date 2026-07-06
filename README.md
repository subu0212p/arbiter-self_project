# Arbiter

A small online judge — sandboxed code execution, an async job queue, a REST API, and a web frontend — built from scratch to explore how systems like LeetCode/Codeforces actually run untrusted user code safely.

Pick a problem, write a solution in Python or C++, submit it, and get back a real verdict (AC/WA/TLE/MLE/RE/CE) from code that actually ran, not a canned response.

## Features

- Sandboxed code execution with two swappable backends behind a common interface: OS resource limits (CPU/memory/process count) on Linux/Mac, with a timeout + memory-watchdog fallback on Windows; a container-based (Docker) backend for stronger isolation
- Judge supporting Python and C++, with full AC / WA / TLE / MLE / RE / CE verdict handling
- Async job queue with a worker-thread pool, so submissions are judged without blocking the API
- Flask REST API (`/api/problems`, `/api/submit`, `/api/submissions/<id>`)
- Plain HTML/CSS/JS frontend — no build step, no framework
- 10 problems spanning Easy to Hard, including a stack-based DSA problem (balanced parentheses)

## Project layout

| File | Description |
|---|---|
| `executor_base.py` | The `Executor` interface both sandboxing backends implement. |
| `subprocess_executor.py` | OS resource-limit-based sandbox (tested and verified) with a Windows-compatible fallback path. |
| `docker_executor.py` | Container-based sandbox (untested in this build environment — no Docker available; see module docstring). |
| `judge.py` | Runs a submission against a problem's test cases and decides the verdict. |
| `problems.py` / `problems_data.json` | The problem bank. |
| `queue_worker.py` | Async job queue with worker threads. |
| `app.py` | Flask REST API + serves the frontend. |
| `static/` | Frontend (HTML/CSS/JS). |
| `tests.py` | Automated test suite. |

## Getting started

Requires Python 3.8+, Flask, and (for C++ submissions) a `g++` compiler on PATH.

**Install dependencies:**
```
pip install flask                    # Mac/Linux
pip install flask psutil             # Windows (psutil powers the memory-limit fallback)
```

**Run the tests:**
```
python3 tests.py        # Windows: python tests.py
```

**Run the app:**
```
python3 app.py           # Windows: python app.py
```
Open `http://127.0.0.1:5050`, pick a problem, write a solution, hit Submit.

> On Windows, C++ submissions require a `g++` toolchain (e.g. via MSYS2/MinGW-w64) on PATH — Python submissions have no such requirement.

## Verified behavior

Every executor verdict path (OK, RE, TLE, MLE, CE) tested against real running code. Judge AC/WA logic tested against both correct and incorrect solutions. Queue tested submit-to-done. Full Flask app tested end-to-end by starting the real server and exercising every endpoint. All 10 problems' correct solutions verified in both Python and C++ against the live server. `DockerExecutor` is the one component not exercised here, due to no Docker being available in the build environment.

## Design notes

- Sandboxing is behind a pluggable `Executor` interface, so the judge, queue, and API never need to know which backend is running code.
- Memory-limit detection on Linux is a heuristic (checking for `MemoryError`/`bad_alloc` in stderr), since OS resource limits don't provide one unambiguous "killed for memory" signal the way a container OOM killer does.
- Frontend is intentionally framework-free — the differentiated engineering here is the sandboxing, the queue, and the judging logic, not the UI.

A deeper write-up of the architecture, the algorithms involved, and the trade-offs behind each decision lives in [`learning-notes/`](learning-notes/).
