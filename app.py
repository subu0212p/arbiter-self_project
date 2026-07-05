"""
app.py — Flask REST API + static frontend server, tying the whole
project together.

Read OVERVIEW.md, Milestone 6, before this file.
"""

from flask import Flask, jsonify, request, send_from_directory

import problems as problems_mod
from subprocess_executor import SubprocessExecutor
from queue_worker import SubmissionQueue

app = Flask(__name__, static_folder="static", static_url_path="")

PROBLEMS = problems_mod.load_problems()
EXECUTOR = SubprocessExecutor()
SUBMISSION_QUEUE = SubmissionQueue(EXECUTOR, PROBLEMS, num_workers=4)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/problems")
def api_list_problems():
    return jsonify(problems_mod.list_problems_summary(PROBLEMS))


@app.route("/api/problems/<problem_id>")
def api_get_problem(problem_id):
    problem = PROBLEMS.get(problem_id)
    if problem is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(problems_mod.public_problem_view(problem))


@app.route("/api/submit", methods=["POST"])
def api_submit():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    language = data.get("language", "python")
    problem_id = data.get("problem_id")

    if problem_id not in PROBLEMS:
        return jsonify({"error": "unknown problem"}), 400
    if not code.strip():
        return jsonify({"error": "empty submission"}), 400
    if language not in ("python", "cpp"):
        return jsonify({"error": f"unsupported language: {language}"}), 400

    submission_id = SUBMISSION_QUEUE.submit(code, language, problem_id)
    return jsonify({"submission_id": submission_id})


@app.route("/api/submissions/<submission_id>")
def api_get_submission(submission_id):
    result = SUBMISSION_QUEUE.get_result(submission_id)
    if result is None:
        return jsonify({"error": "unknown submission"}), 404
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
