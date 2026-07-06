# Arbiter — Project Overview

Read this file first, before looking at any code. It explains *what* we're building and *why*, in plain English, one milestone at a time. Read a section fully before opening the matching code file.

---

## What is an online judge, actually?

Think LeetCode, Codeforces, or HackerRank: you write code in a browser, hit submit, and within a few seconds you get back "Accepted" or "Wrong Answer" (or something else, like a crash or a timeout). Behind that simple experience is a real, non-trivial system: your code has to be **executed somewhere**, against test cases the platform controls, **safely** — because the whole point is that this code came from a stranger on the internet, and letting a stranger's arbitrary code run unrestricted on your server is a serious security problem.

Arbiter is a small, real version of that system: a web app where you pick a problem, write a solution, submit it, and get back a genuine verdict from code that actually ran (not a canned response).

### Why this matters for your interviews

This is the one project of the three that's a real full-stack web application (frontend + backend + a genuinely hard infrastructure problem: safely running untrusted code), so it demonstrates a different, broader slice of skills than CacheForge or Strata — REST API design, background job processing, and specifically the security question of "how do you run code you don't trust." That last one is a legitimately interesting systems question that most student projects never touch.

### Is this a website? What does it look like when it runs?

**Yes — this is the one that actually is a web app.** You open a browser, see a list of problems, click one, write code in a text box, hit Submit, and watch a verdict appear. `app.py` runs a small web server (Flask) that serves both the page itself and a JSON API the page's JavaScript calls.

---

## What we built, milestone by milestone

### Milestone 1: The Sandboxed Executor

**Why can't you just run submitted code with a plain `subprocess.run(...)`, no precautions?** Because nothing would stop it from running forever (an infinite loop ties up your server), allocating unlimited memory (crashing your whole machine), or worse. **Sandboxing** means constraining what a piece of untrusted code is allowed to do before you let it run at all.

**What we built:** `subprocess_executor.py`'s `SubprocessExecutor` runs code as a subprocess, but with OS-level resource limits applied via Python's `resource` module *inside the child process, right before it actually executes the user's code* (a `preexec_fn`, which is the only point at which this is possible — you can't apply a limit to a process from outside after it's already running unrestricted): a CPU time cap (`RLIMIT_CPU`), a memory cap (`RLIMIT_AS`, limiting total address space), and a process-count cap (`RLIMIT_NPROC`, so the code can't fork-bomb its way around the other limits). On top of that, `subprocess.run(..., timeout=...)` enforces a wall-clock deadline independent of CPU time (so something that's sleeping, not computing, still eventually gets killed).

**Why an `Executor` base class/interface, rather than hard-coding one way of running code everywhere?** So *how* code gets isolated is swappable without touching the judging logic that sits on top of it (`judge.py` just calls `executor.run(...)` and doesn't know or care which concrete executor it's talking to). This project ships two: `SubprocessExecutor` (see above — tested, verified working) and `DockerExecutor` (Milestone 8 — a stronger, container-based sandbox, honestly documented as *not* testable in the environment this project was built in, since Docker wasn't installed there).

**A genuine, named limitation, verified by testing:** distinguishing "killed for using too much memory" from "crashed for some other reason" is *not* perfectly clean with OS resource limits — there's no single unambiguous signal for it the way a container runtime's OOM killer provides. We detect it with a heuristic (checking whether `MemoryError` or `bad_alloc` shows up in the crashed program's error output), which was tested directly and confirmed to work for both Python and C++ — but it's still a heuristic, not a guarantee, and is worth naming as such if asked.

**A second genuine, named limitation — this one about the OS, not the heuristic:** `resource.setrlimit()` (and `RLIMIT_CPU`/`RLIMIT_AS`/`RLIMIT_NPROC`) only exist on POSIX systems (Linux, Mac) — Windows has no equivalent in the standard library at all. `subprocess_executor.py` handles this honestly with two code paths: the `resource`-based one described above on Linux/Mac, and a Windows fallback that uses the wall-clock `timeout` (still catches infinite loops) plus a background thread that polls the child process's memory via `psutil` and kills it if it goes over the limit. The one piece that doesn't have a good Windows equivalent is the fork-bomb defense (`RLIMIT_NPROC`) — see `CONCEPTS_QA.md`, Milestone 1, for the full trade-off. This is exactly the kind of "why doesn't this just work everywhere" question a project like this should be ready to answer in an interview.

---

### Milestone 2: Verdicts

**What we built:** `judge.py` compares a submission's actual output (after trimming trailing whitespace per line, since that shouldn't fail an otherwise-correct answer) against the expected output for a test case, and assigns one of: **AC** (Accepted — every test case passed), **WA** (Wrong Answer — output didn't match), **TLE** (Time Limit Exceeded), **MLE** (Memory Limit Exceeded), **RE** (Runtime Error — the program crashed), or **CE** (Compile Error — for compiled languages like C++, when the code doesn't even build).

**Why support more than one language, and why Python + C++ specifically?** To prove the executor abstraction actually is general-purpose and not secretly hardcoded around one language's quirks. Python (interpreted, no compile step) and C++ (compiled, so there's a whole extra failure mode — CE — to handle) are different enough to genuinely exercise that.

---

### Milestone 3: The Problem Bank

**What we built:** `problems_data.json` holds a small set of problems (statement, difficulty, and a list of test cases with input/expected-output pairs). `problems.py` loads it and exposes a "public view" of a problem that only reveals *one* sample test case, never the full hidden test suite a submission is actually judged against — matching how real judges work (showing every hidden test case would let someone just hardcode the expected outputs instead of solving the problem).

---

### Milestone 4: Tying Judging Together

**What we built:** `judge.judge_submission()` runs a submission against every test case of a problem, in order, and stops at the *first* failure — matching real judges, which don't keep burning compute on a submission already known to be broken. It returns the overall verdict plus how many test cases were passed before that point.

---

### Milestone 5: The Job Queue

**Why not just judge a submission synchronously, right inside the HTTP request that submits it?** Because judging can take real time (compiling C++, running against several test cases, each potentially up to the time limit) — making the client's browser sit there waiting on one HTTP request for several seconds is a bad experience, and ties up a web server thread the whole time. The standard fix: the submit endpoint enqueues the work and returns *immediately* with an ID; the actual judging happens on a background worker; the client polls (or could use a websocket) for the result using that ID.

**What we built:** `queue_worker.py`'s `SubmissionQueue` wraps Python's built-in thread-safe `queue.Queue` with a small pool of worker threads that continuously pull jobs off it and run them through `judge_submission`. This is the exact same *shape* as a production task queue (Celery+Redis, AWS SQS+workers) — a producer enqueues, independent workers consume — just without needing any external infrastructure for a learning project. Swapping this for a real distributed queue later wouldn't require changing how `judge.py` or `app.py` use it.

---

### Milestone 6: The REST API

**What we built:** `app.py` is a small Flask application exposing `GET /api/problems` (list), `GET /api/problems/<id>` (detail, public view only), `POST /api/submit` (enqueue a submission, returns a submission ID immediately), and `GET /api/submissions/<id>` (poll for status/result).

**Why does `/api/submit` validate the problem ID, language, and non-empty code before even touching the queue?** Fail fast, with a clear error, on obviously-bad input, rather than letting garbage propagate into the judging pipeline and produce a confusing failure two layers deeper.

---

### Milestone 7: The Web Frontend

**What we built:** a plain HTML/CSS/JavaScript single page (`static/index.html`, `style.css`, `app.js`) — no React, no build step, no `npm install`. It fetches the problem list, lets you open one, write code in a textarea, hit submit, and polls `/api/submissions/<id>` every half-second until a verdict comes back.

**Why plain HTML/JS instead of React, given Node is available?** A deliberate scoping choice: this keeps the project runnable with nothing beyond Python installed (`python3 app.py` and open a browser — no build pipeline, no `node_modules`, nothing that can go stale or fail to install). The actual engineering substance of this project — the sandboxed executor, the queue, the judging logic — doesn't get any more or less impressive by swapping the frontend framework; keeping the frontend simple is time spent instead on the parts that are genuinely hard.

---

### Milestone 8: Docker Executor, Tests, and Polish

**What we built:** `docker_executor.py`'s `DockerExecutor` implements the same `Executor` interface as `SubprocessExecutor`, but runs code inside a throwaway Docker container (`docker run --rm --network none --memory=<limit> ...`) instead of a plain OS process — stronger isolation (its own filesystem view, its own process namespace, no network access at all), at the cost of a heavier, slower-to-start execution path.

**Stated plainly, because it matters for how you talk about this:** this executor was written but **could not be tested** in the environment this project was built in, because Docker wasn't installed there. It's included because it represents the realistic production approach and is genuinely useful to have implemented and documented — but if you use this project in an interview, be upfront that this specific piece is unverified until you've run it yourself on a machine with Docker. `tests.py` therefore only covers `SubprocessExecutor`, which *was* fully tested — including a real memory-limit violation and a real infinite loop being killed on schedule, not mocked-out versions of those scenarios.

**What was actually verified, end-to-end, before this was called done:** every executor verdict path (OK, RE, TLE, MLE, CE) tested directly against real running code; the judge's AC/WA logic tested against both a correct and an incorrect solution; the queue tested end-to-end (submit -> poll -> done); and the full Flask app tested by actually starting the server and hitting every endpoint with `curl`, including a full submit-and-poll cycle for both a correct and an incorrect submission, confirming the verdicts came back exactly as expected.
