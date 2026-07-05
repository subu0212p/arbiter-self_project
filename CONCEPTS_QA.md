# Interview Q&A — Arbiter

Read the matching section in `OVERVIEW.md` first. Then use this file to test yourself — cover the "A:" with your hand and try answering in your own words before reading it.

---

## Milestone 1: The Sandboxed Executor

**Q: Why is running untrusted, submitted code fundamentally dangerous, and what specifically are you protecting against?**
A: Code submitted by an anonymous user could try to run forever (denial of service), allocate unbounded memory (crashing the host), spawn unlimited processes (a fork bomb), read/write files it shouldn't, or try to access the network. Sandboxing means constraining what that code is *allowed* to do before it ever runs, rather than trusting it to behave.

**Q: What is `preexec_fn` and why does the resource limiting have to happen there specifically?**
A: `preexec_fn` is a function `subprocess.run()` calls inside the newly forked child process, after `fork()` but before the child actually `exec()`s into running the target program. That's the only point at which `resource.setrlimit()` can apply a limit *to that specific child process* without affecting the parent (our own judge server process) — you can't retroactively apply a resource limit to an already-running, unrestricted process from outside it.

**Q: Name the three specific resource limits used, and what each protects against.**
A: `RLIMIT_CPU` caps total CPU time, protecting against code that computes forever (an infinite loop that's actually doing work). `RLIMIT_AS` caps total address space (effectively memory), protecting against unbounded memory allocation. `RLIMIT_NPROC` caps the number of processes/threads the code can create, protecting against fork bombs that might otherwise let code work around the other two limits by just spawning more copies of itself.

**Q: Why is there a `timeout=` on `subprocess.run()` in addition to `RLIMIT_CPU`?**
A: `RLIMIT_CPU` only limits actual CPU *computation* time — a process that's sleeping or blocked waiting on I/O isn't burning CPU time, so it could still run past a CPU limit's window in wall-clock terms. `timeout=` enforces a wall-clock deadline independent of that, catching cases the CPU limit alone wouldn't.

**Q: You mentioned memory-limit detection is a "heuristic." Explain exactly what that means and why it's not a hard guarantee.**
A: We check whether the crashed program's stderr contains `MemoryError` (Python) or `bad_alloc` (C++), since exceeding `RLIMIT_AS` typically surfaces as one of those catchable exceptions rather than one single unambiguous OS-level signal. If a program happened to print similar text for an unrelated reason, or crashed via some other path when it hit the memory ceiling, this heuristic could misclassify it. This was tested and confirmed to work for the specific real memory-limit-violation case we constructed, but "tested for the cases I constructed" and "provably correct for all cases" are different claims, and it's important not to conflate them.

**Q: Why does the executor interface exist as a base class instead of the judge calling `SubprocessExecutor` directly?**
A: So the judging logic (`judge.py`) depends only on the `Executor` interface (`run()` returning an `ExecutionResult`), not on any specific sandboxing technology. Swapping `SubprocessExecutor` for `DockerExecutor` — or something stronger in the future — requires touching zero lines of `judge.py`, `queue_worker.py`, or `app.py`.

**Q: What changes on Windows? Why can't the same code just work everywhere?**
A: `resource.setrlimit()` and the constants used here (`RLIMIT_CPU`, `RLIMIT_AS`, `RLIMIT_NPROC`) are POSIX-only — the `resource` module doesn't exist on Windows at all, so importing it crashes immediately on a Windows machine. `subprocess_executor.py` handles this with two code paths chosen at import time (`IS_POSIX = os.name == "posix"`): the original `preexec_fn`/`resource` approach on Linux/Mac, and a Windows fallback (`_run_windows()`) that approximates the same protections differently — a wall-clock `timeout` still catches infinite loops (TLE), and a background thread polls the child process's memory via `psutil` and kills it if it crosses the limit (MLE). One protection genuinely isn't recreated on Windows: `RLIMIT_NPROC` (the fork-bomb defense) has no practical Windows equivalent here, so that case is only enforced on the POSIX path. That's a real, honest trade-off worth naming directly if asked, not something to gloss over.

**Q: Why is the Windows memory watchdog "polling-based" instead of a hard limit like `RLIMIT_AS`?**
A: The background thread checks the child process's memory usage every 20 milliseconds and kills it once it's over the limit — that's a check-then-react loop, not an instant OS-enforced ceiling. A process that allocates a very large block of memory in a single instant, between two checks, could in principle spike past the limit for a brief moment before getting caught. `RLIMIT_AS` on Linux has no such gap — the kernel refuses the allocation the instant it would exceed the limit. It's a meaningfully weaker guarantee, which is part of why real production sandboxing for this kind of problem tends to run on Linux (or in containers) rather than depending on a Windows-only deployment.

---

## Milestone 2: Verdicts

**Q: List the verdicts this judge can produce and what each means.**
A: AC (Accepted — every test case passed), WA (Wrong Answer — ran fine but produced incorrect output), TLE (Time Limit Exceeded), MLE (Memory Limit Exceeded), RE (Runtime Error — crashed), CE (Compile Error — didn't even build, for compiled languages).

**Q: Why trim trailing whitespace before comparing output, instead of requiring an exact byte-for-byte match?**
A: A correct solution shouldn't fail a judge just because it printed a trailing space or a different number of trailing newlines than the expected output file happens to have — that's an artifact of formatting, not incorrect logic. Real judges normalize this the same way.

---

## Milestone 3: The Problem Bank

**Q: Why does the API only ever expose one sample test case per problem, never the full hidden suite?**
A: If every test case were visible, a submission could simply hardcode the expected outputs for each visible input instead of actually solving the general problem — the hidden test cases are what make "passing" mean anything.

---

## Milestone 4: Judging Logic

**Q: Why does `judge_submission` stop at the first failing test case instead of running all of them and reporting every failure?**
A: Once a submission has failed one test case, it's already not going to receive AC — continuing to burn compute (and sandboxed process time) running the remaining test cases provides limited value for a lot of cost. Real judges behave the same way, which is part of why judging a submission with many test cases can still be fast even for a wrong answer.

---

## Milestone 5: The Job Queue

**Q: Why not just judge a submission inside the HTTP request that submits it?**
A: Judging can take real time (potentially multiple test cases, each up to the time limit, plus compilation for compiled languages) — blocking an HTTP request (and the browser waiting on it) for several seconds is a poor experience and ties up a web server thread the entire time. Enqueueing the work and returning an ID immediately lets the client poll asynchronously while the server stays responsive to other requests.

**Q: What does this project's job queue have in common with a production system like Celery+Redis or SQS+workers?**
A: The same fundamental shape: a producer enqueues a unit of work, and a pool of independent workers pulls from the queue and processes jobs concurrently, decoupled from whoever submitted the work. The specific queue implementation (in-memory `queue.Queue` vs. Redis-backed vs. SQS) is an implementation detail behind that shape — which is exactly why swapping it out later wouldn't require rewriting the code that uses it.

**Q: Why does each worker thread hold the lock only briefly (to update a status dict), rather than holding it for the entire judging duration?**
A: Judging a submission can take seconds, and holding a lock that long would block every other thread (including the web server thread trying to read a status) from making any progress during that whole time. The lock only needs to protect the shared `_results` dictionary itself during the brief moment it's actually being read or written — the actual (slow) judging work happens outside the lock entirely.

---

## Milestone 6: The REST API

**Q: Why validate the problem ID, language, and code emptiness in `/api/submit` before enqueueing anything?**
A: Failing fast with a clear, specific error message on obviously invalid input is better than letting bad input propagate into the queue and the judging pipeline, where the resulting failure would be more confusing and harder to trace back to its actual cause.

**Q: Walk me through what happens, end to end, from a user clicking Submit to seeing a verdict.**
A: The frontend POSTs code/language/problem_id to `/api/submit`. The Flask handler validates the input and calls `SubmissionQueue.submit()`, which generates a UUID, records a "queued" status, pushes the job onto the internal queue, and returns the UUID immediately. A worker thread picks up the job, sets status to "running," calls `judge_submission()` (which runs the code through the sandboxed executor against each test case), and writes the final verdict into the results dict under that UUID with status "done." Meanwhile, the frontend has been polling `GET /api/submissions/<uuid>` every 500ms; once it sees status "done," it renders the verdict.

---

## Milestone 7: The Web Frontend

**Q: Why plain HTML/CSS/JS instead of React, given this environment has Node available?**
A: A deliberate scoping decision, not a limitation of skill: it keeps the whole project runnable with nothing beyond Python (`python3 app.py`, open a browser) — no build step, no `npm install`, nothing that can go stale, fail to install, or require a specific Node version to reproduce. The genuinely hard, differentiating engineering in this project is the sandboxed executor, the queue, and the judging logic — the frontend framework choice doesn't change how impressive or correct any of that is.

**Q: Why does the frontend poll for results instead of using a WebSocket for real-time push?**
A: Polling every 500ms is far simpler to implement and reason about, and for a judge where results typically arrive within a few seconds, the latency difference between polling and push is imperceptible to a user. A WebSocket would be the right call for a system needing sub-100ms updates or a very high volume of concurrent long-lived connections — worth naming as the natural next step if asked how you'd scale this.

---

## Milestone 8: Docker Executor and Verification

**Q: Why include a Docker-based executor you couldn't test yourself?**
A: Because it represents the realistic, production-grade approach to this problem (stronger isolation via containers), and having it implemented and documented — while being explicit about the fact that it's unverified until run on a machine with Docker — is more honest and more useful than either pretending it was tested, or leaving it out and only ever discussing container-based sandboxing in the abstract.

**Q: What specifically is stronger about container-based isolation versus the OS resource-limit approach you tested?**
A: A container gets its own filesystem view (can't see or tamper with the host's real files), its own process namespace (can't see or signal processes outside the container, which meaningfully changes what a fork bomb or process-enumeration attack could even attempt), and with `--network none`, no network access at all. A resource-limited subprocess still runs directly against the host's real filesystem and kernel — the limits constrain *how much* it can consume, but not what it can, in principle, see or reach.

**Q: If Docker had been available, what would you have changed about how you tested it?**
A: I'd run the exact same test suite that exists for `SubprocessExecutor` — the OK/RE/TLE/MLE/CE cases — against `DockerExecutor` instead, to confirm the two executors actually produce equivalent verdicts for equivalent code, since that equivalence is the entire point of having them share one interface.
