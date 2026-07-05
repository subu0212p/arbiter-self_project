"""
queue_worker.py — an in-process job queue with a small pool of worker
threads, so submitting code returns instantly and the actual judging
(which can take seconds) happens in the background.

Read OVERVIEW.md, Milestone 5, before this file.

This is the same *shape* as a production task queue (Celery + Redis, AWS
SQS + workers, etc.) - a producer enqueues work, a pool of workers pulls
from the queue and processes it independently - just without needing any
external infrastructure for a learning project. Swapping this out for a
real distributed queue later wouldn't change how judge.py or app.py use it.
"""

import queue
import threading
import uuid

import judge as judge_mod


class SubmissionQueue:
    def __init__(self, executor, problems: dict, num_workers: int = 4):
        self._executor = executor
        self._problems = problems
        self._queue: "queue.Queue" = queue.Queue()
        self._results: dict = {}
        self._lock = threading.Lock()
        self._workers = [
            threading.Thread(target=self._worker_loop, daemon=True)
            for _ in range(num_workers)
        ]
        for w in self._workers:
            w.start()

    def submit(self, code: str, language: str, problem_id: str) -> str:
        submission_id = str(uuid.uuid4())
        with self._lock:
            self._results[submission_id] = {"status": "queued"}
        self._queue.put((submission_id, code, language, problem_id))
        return submission_id

    def get_result(self, submission_id: str):
        with self._lock:
            return self._results.get(submission_id)

    def _worker_loop(self):
        while True:
            submission_id, code, language, problem_id = self._queue.get()
            with self._lock:
                self._results[submission_id]["status"] = "running"

            problem = self._problems.get(problem_id)
            if problem is None:
                with self._lock:
                    self._results[submission_id] = {
                        "status": "error", "message": "unknown problem"
                    }
                continue

            outcome = judge_mod.judge_submission(self._executor, code, language, problem)
            with self._lock:
                self._results[submission_id] = {"status": "done", **outcome}
