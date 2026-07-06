// app.js — the whole frontend. No build step, no framework: fetch() calls
// to the Flask API in app.py, and plain DOM manipulation. See OVERVIEW.md,
// Milestone 7, for why that's a deliberate choice for this project rather
// than a limitation.

const problemListEl = document.getElementById("problems");
const problemListSectionEl = document.getElementById("problem-list");
const problemDetailEl = document.getElementById("problem-detail");
const backBtn = document.getElementById("back-btn");
const titleEl = document.getElementById("problem-title");
const difficultyEl = document.getElementById("problem-difficulty");
const statementEl = document.getElementById("problem-statement");
const sampleEl = document.getElementById("problem-sample");
const codeEl = document.getElementById("code");
const languageEl = document.getElementById("language");
const submitBtn = document.getElementById("submit-btn");
const verdictEl = document.getElementById("verdict");

let currentProblemId = null;

async function loadProblems() {
  const res = await fetch("/api/problems");
  const problems = await res.json();
  problemListEl.innerHTML = "";
  for (const p of problems) {
    const li = document.createElement("li");

    const titleSpan = document.createElement("span");
    titleSpan.className = "problem-title";
    titleSpan.textContent = p.title;

    const badge = document.createElement("span");
    badge.className = `badge badge-${p.difficulty.toLowerCase()}`;
    badge.textContent = p.difficulty;

    li.appendChild(titleSpan);
    li.appendChild(badge);
    li.addEventListener("click", () => openProblem(p.id));
    problemListEl.appendChild(li);
  }
}

async function openProblem(id) {
  const res = await fetch(`/api/problems/${id}`);
  const problem = await res.json();
  currentProblemId = id;
  titleEl.textContent = problem.title;
  difficultyEl.innerHTML = "";
  const badge = document.createElement("span");
  badge.className = `badge badge-${problem.difficulty.toLowerCase()}`;
  badge.textContent = problem.difficulty;
  difficultyEl.appendChild(badge);
  statementEl.textContent = problem.statement;
  sampleEl.textContent =
    `Input:\n${problem.samples[0].input}\nExpected output:\n${problem.samples[0].expected_output}`;
  verdictEl.textContent = "";
  verdictEl.className = "";
  problemListSectionEl.hidden = true;
  problemDetailEl.hidden = false;
}

function showList() {
  problemDetailEl.hidden = true;
  problemListSectionEl.hidden = false;
}

async function submitCode() {
  submitBtn.disabled = true;
  verdictEl.className = "";
  verdictEl.textContent = "Submitting...";

  const res = await fetch("/api/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      code: codeEl.value,
      language: languageEl.value,
      problem_id: currentProblemId,
    }),
  });
  const data = await res.json();
  if (data.error) {
    verdictEl.textContent = `Error: ${data.error}`;
    submitBtn.disabled = false;
    return;
  }

  pollSubmission(data.submission_id);
}

async function pollSubmission(submissionId) {
  verdictEl.textContent = "Judging...";
  const poll = async () => {
    const res = await fetch(`/api/submissions/${submissionId}`);
    const result = await res.json();

    if (result.status === "done") {
      renderVerdict(result);
      submitBtn.disabled = false;
    } else if (result.status === "error") {
      verdictEl.textContent = `Error: ${result.message}`;
      submitBtn.disabled = false;
    } else {
      setTimeout(poll, 500);
    }
  };
  poll();
}

function renderVerdict(result) {
  verdictEl.textContent = `${result.verdict} — passed ${result.passed}/${result.total} test cases`;
  verdictEl.className = result.verdict === "AC" ? "verdict-ac" : "verdict-fail";
}

submitBtn.addEventListener("click", submitCode);
backBtn.addEventListener("click", showList);
loadProblems();
