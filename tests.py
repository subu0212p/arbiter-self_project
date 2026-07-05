"""
Automated tests for Arbiter — run with: python3 tests.py

These actually execute real (harmless) code through SubprocessExecutor to
verify the sandbox genuinely enforces its limits, not just that the code
compiles - a mocked-out test would prove much less here. DockerExecutor is
intentionally NOT covered here (see docker_executor.py's module docstring
for why - no Docker in this build environment).
"""

import time

import judge as judge_mod
from queue_worker import SubmissionQueue
from subprocess_executor import SubprocessExecutor

executor = SubprocessExecutor()


def test_python_ok():
    result = executor.run("print('hello')", "python", "", time_limit=2.0, memory_limit_mb=256)
    assert result.verdict == "OK"
    assert result.stdout.strip() == "hello"
    print("test_python_ok: PASS")


def test_python_reads_stdin():
    code = "n = input()\nprint(int(n) * 2)"
    result = executor.run(code, "python", "21\n", time_limit=2.0, memory_limit_mb=256)
    assert result.verdict == "OK"
    assert result.stdout.strip() == "42"
    print("test_python_reads_stdin: PASS")


def test_python_runtime_error():
    result = executor.run("1 / 0", "python", "", time_limit=2.0, memory_limit_mb=256)
    assert result.verdict == "RE"
    assert "ZeroDivisionError" in result.stderr
    print("test_python_runtime_error: PASS")


def test_python_time_limit_exceeded():
    code = "while True:\n    pass"
    start = time.time()
    result = executor.run(code, "python", "", time_limit=1.0, memory_limit_mb=256)
    elapsed = time.time() - start
    assert result.verdict == "TLE"
    assert elapsed < 3.0, "should be killed close to the time limit, not run forever"
    print("test_python_time_limit_exceeded: PASS")


def test_python_memory_limit_exceeded():
    code = "x = bytearray(500 * 1024 * 1024)"  # try to allocate 500MB
    result = executor.run(code, "python", "", time_limit=5.0, memory_limit_mb=64)
    assert result.verdict == "MLE", f"expected MLE, got {result.verdict}: {result.stderr[-300:]}"
    print("test_python_memory_limit_exceeded: PASS")


def test_cpp_compile_and_run():
    code = '#include <iostream>\nint main() { std::cout << "cpp works"; return 0; }'
    result = executor.run(code, "cpp", "", time_limit=5.0, memory_limit_mb=256)
    assert result.verdict == "OK", result.stderr
    assert result.stdout.strip() == "cpp works"
    print("test_cpp_compile_and_run: PASS")


def test_cpp_compile_error():
    result = executor.run("this is not valid c++", "cpp", "", time_limit=5.0, memory_limit_mb=256)
    assert result.verdict == "CE"
    print("test_cpp_compile_error: PASS")


def test_judge_accepted():
    problem = {
        "test_cases": [
            {"input": "3\n4\n", "expected_output": "7"},
            {"input": "10\n20\n", "expected_output": "30"},
        ]
    }
    code = "a = int(input())\nb = int(input())\nprint(a + b)"
    outcome = judge_mod.judge_submission(executor, code, "python", problem)
    assert outcome["verdict"] == "AC"
    assert outcome["passed"] == 2
    print("test_judge_accepted: PASS")


def test_judge_wrong_answer():
    problem = {
        "test_cases": [
            {"input": "3\n4\n", "expected_output": "7"},
            {"input": "10\n20\n", "expected_output": "999"},  # deliberately wrong expectation
        ]
    }
    code = "a = int(input())\nb = int(input())\nprint(a + b)"
    outcome = judge_mod.judge_submission(executor, code, "python", problem)
    assert outcome["verdict"] == "WA"
    assert outcome["passed"] == 1
    print("test_judge_wrong_answer: PASS")


def test_submission_queue_end_to_end():
    problems = {
        "add": {"id": "add", "test_cases": [{"input": "2\n2\n", "expected_output": "4"}]},
    }
    q = SubmissionQueue(executor, problems, num_workers=2)
    submission_id = q.submit("a=int(input());b=int(input());print(a+b)", "python", "add")

    result = None
    for _ in range(50):
        result = q.get_result(submission_id)
        if result["status"] == "done":
            break
        time.sleep(0.1)
    else:
        raise AssertionError("submission never finished")

    assert result["verdict"] == "AC"
    print("test_submission_queue_end_to_end: PASS")


if __name__ == "__main__":
    test_python_ok()
    test_python_reads_stdin()
    test_python_runtime_error()
    test_python_time_limit_exceeded()
    test_python_memory_limit_exceeded()
    test_cpp_compile_and_run()
    test_cpp_compile_error()
    test_judge_accepted()
    test_judge_wrong_answer()
    test_submission_queue_end_to_end()
    print("\nAll tests passed.")
