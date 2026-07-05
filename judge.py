"""
judge.py — runs a submission against every test case of a problem and
decides the final verdict.

Read OVERVIEW.md, Milestones 2 and 4, before this file.
"""


def normalize_output(text: str) -> str:
    """Trim trailing whitespace on each line and at the end of the whole
    output - standard judge behavior, since differing only in trailing
    spaces or a missing final newline shouldn't fail an otherwise-correct
    submission."""
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).rstrip()


def judge_submission(executor, code: str, language: str, problem: dict,
                      time_limit: float = 2.0, memory_limit_mb: int = 256) -> dict:
    """Runs test cases in order and stops at the FIRST failure - matching
    real judges, which don't keep burning compute on a submission that's
    already known to be wrong/broken. Returns a dict with the overall
    verdict, how many test cases passed before that, and per-test detail."""
    results = []
    test_cases = problem["test_cases"]

    for i, test_case in enumerate(test_cases):
        exec_result = executor.run(
            code, language, test_case["input"], time_limit, memory_limit_mb
        )

        if exec_result.verdict != "OK":
            results.append({
                "test_case": i,
                "verdict": exec_result.verdict,
                "stderr": exec_result.stderr,
                "time_taken": exec_result.time_taken,
            })
            return {
                "verdict": exec_result.verdict,
                "passed": len(results) - 1,
                "total": len(test_cases),
                "results": results,
            }

        actual = normalize_output(exec_result.stdout)
        expected = normalize_output(test_case["expected_output"])
        if actual != expected:
            results.append({
                "test_case": i,
                "verdict": "WA",
                "expected": expected,
                "actual": actual,
                "time_taken": exec_result.time_taken,
            })
            return {
                "verdict": "WA",
                "passed": len(results) - 1,
                "total": len(test_cases),
                "results": results,
            }

        results.append({"test_case": i, "verdict": "OK", "time_taken": exec_result.time_taken})

    return {
        "verdict": "AC",
        "passed": len(test_cases),
        "total": len(test_cases),
        "results": results,
    }
