"""
problems.py — the problem bank: statements + test cases.

Read OVERVIEW.md, Milestone 3, before this file.

Stored as a plain JSON file (problems_data.json), same reasoning as every
other "why JSON instead of a database" choice in these projects: you can
open it and read exactly what's in it, which matters more for a learning
project than the query performance a real database would buy at scale.
"""

import json
import os

PROBLEMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "problems_data.json")


def load_problems() -> dict:
    with open(PROBLEMS_FILE) as f:
        problems = json.load(f)
    return {p["id"]: p for p in problems}


def list_problems_summary(problems: dict) -> list:
    return [
        {"id": p["id"], "title": p["title"], "difficulty": p["difficulty"]}
        for p in problems.values()
    ]


def public_problem_view(problem: dict) -> dict:
    """Strips a problem down to what a client is allowed to see - the full
    statement and difficulty, but only ONE sample test case, not the full
    hidden test suite a submission is actually judged against. Real judges
    do the same thing: showing all hidden test cases would let someone
    just hardcode outputs instead of solving the problem."""
    return {
        "id": problem["id"],
        "title": problem["title"],
        "difficulty": problem["difficulty"],
        "statement": problem["statement"],
        "samples": problem["test_cases"][:1],
    }
