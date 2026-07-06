# Arbiter

A small online judge — like a mini LeetCode/Codeforces — built from scratch: real sandboxed code execution (not a canned response), a job queue, a Flask REST API, and a web frontend, built to deeply understand (and be able to explain in interviews) how systems like this actually run untrusted code safely.

**This one really is a web app.** Open a browser, pick a problem, write code, hit submit, watch a real verdict come back.

**Read in this order:**
1. `OVERVIEW.md` — what an online judge actually is, and a milestone-by-milestone explanation of what we built and why.
2. `CONCEPTS_QA.md` — interview-style Q&A for every concept, in the same order.
3. `RESUME_POINTS.md` — polished bullet points for your resume.

## Project layout

| File | What it is |
|---|---|
| `executor_base.py` | The `Executor` interface both sandboxing backends implement. |
| `subprocess_executor.py` | **Tested and verified.** Sandboxes code using OS resource limits (CPU/memory/process count) on Linux/Mac; falls back to a timeout + psutil memory watchdog on Windows, since `resource.setrlimit` is POSIX-only (see CONCEPTS_QA.md, Milestone 1). |
| `docker_executor.py` | Container-based sandbox. **Not tested here — no Docker in this build environment.** Verify it yourself before relying on it (see its module docstring). |
| `judge.py` | Runs a submission against a problem's test cases and decides AC/WA/TLE/MLE/RE/CE. |
| `problems.py` / `problems_data.json` | The problem bank (statement + test cases). |
| `queue_worker.py` | In-process job queue + worker threads, so submissions are judged asynchronously. |
| `app.py` | Flask REST API (`/api/problems`, `/api/submit`, `/api/submissions/<id>`) + serves the frontend. |
| `static/` | Plain HTML/CSS/JS frontend — no build step. |
| `tests.py` | Automated tests covering the (tested) subprocess executor, judge logic, and the queue end-to-end. |

## How to run it

**On Windows, use `python` instead of `python3` below** (Windows has no `python3` alias — just `python`). You'll also need `psutil`, used for the memory-limit fallback described above.

**1. Install dependencies (one-time):**

Mac/Linux:
```
pip install flask --break-system-packages
```
Windows:
```
pip install flask psutil
```

**2. Run the automated tests:**

Mac/Linux: `python3 tests.py`   |   Windows: `python tests.py`

You should see 10 `PASS` lines and "All tests passed." (takes a few seconds — some tests deliberately run code until it hits a time/memory limit.)

**3. Run the actual web app:**

Mac/Linux: `python3 app.py`   |   Windows: `python app.py`

Then open `http://127.0.0.1:5050` in a browser. Pick a problem, write a solution, hit Submit.

Try these to see different verdicts on "Sum of Two Numbers":
- `a=int(input());b=int(input());print(a+b)` → **AC**
- `print(0)` → **WA**
- `1/0` → **RE**

### C++ submissions on Windows

C++ submissions need a `g++` compiler on your PATH. Windows doesn't ship one — you'd need to install a toolchain like MinGW-w64 (e.g. via `winget install -e --id MSYS2.MSYS2`, then installing `mingw-w64-gcc` inside it) and add it to PATH, or use WSL. **Python submissions don't need this at all** and are the easiest way to try the judge — if you just want to see it work, stick to Python.

If `g++` isn't found, a C++ submission now cleanly returns a **CE** verdict explaining that, instead of hanging on "Judging..." forever (an earlier bug — an uncaught exception from the missing compiler was silently killing the background worker thread; fixed by catching it in `subprocess_executor.py`'s `_compile_cpp` and, as a second safety net, wrapping the whole judging call in `queue_worker.py` so no single bad submission can ever take down a worker again).

## Verified before calling this done

Every executor verdict path (OK, RE, TLE, MLE, CE) was tested against real running code, not mocked. The judge's AC/WA logic was tested against both a correct and an incorrect solution. The queue was tested submit-to-done. The full Flask app was tested by starting the real server and hitting every endpoint with `curl`, including a complete submit-and-poll cycle for both a correct and incorrect submission. `DockerExecutor` is the one piece **not** verified here — see `OVERVIEW.md`/`CONCEPTS_QA.md`, Milestone 8, for why that's stated honestly rather than hidden.

## Pushing this to GitHub

This project has its own local git history (one commit per milestone). To publish it:
1. Create a new **empty** repository on github.com (don't check "add a README" — we already have one).
2. Copy the commands GitHub shows you under "...or push an existing repository from the command line":
   ```
   git remote add origin https://github.com/<your-username>/arbiter.git
   git branch -M main
   git push -u origin main
   ```
3. Run those from inside this `arbiter` folder.
