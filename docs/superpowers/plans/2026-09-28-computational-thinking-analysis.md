# Computational Thinking Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add evidence-based Computational Thinking feedback to Step 2 of the lesson-plan analysis.

**Architecture:** Keep the existing single Mistral analysis request, extend its JSON contract with six normalized CT entries, and render those entries in a compact expandable panel in the existing Step 2 page. The CT block remains feedback only and is stored together with the existing analysis payload; it does not alter the lesson plan or Step 3 flow.

**Tech Stack:** Python standard library, existing Mistral prompt/JSON handling, plain HTML/CSS/JavaScript, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-28-computational-thinking-analysis-design.md`

## Global Constraints

- Identify CT only when learners perform the corresponding cognitive practice.
- Do not infer CT from keywords, lesson topic, technology use, programming terminology, or teacher activity.
- Use exactly `Present`, `Opportunity`, or `Not identified` as CT statuses.
- Connect each identified CT element to a lesson-plan activity and evidence.
- Suggestions must be small, concrete, and fit the existing lesson goals and activity.
- Keep API keys and other secrets out of logs.

## Review Focus

- A model omits one or more CT dimensions: the backend must return all six in stable order with safe defaults.
- A model returns an unknown status or malformed item: the UI must remain usable and show `Not identified`.
- A CT claim names a topic or teacher action without learner evidence: the prompt must explicitly reject that classification.
- A `Present` item contains an unnecessary refinement: the UI should not invent one; empty refinements stay hidden.
- All six items are `Not identified`: the dedicated panel must still render and make that result visible.

---

### Task 1: Add CT response normalization

**Files:**
- Modify: `app/server/mistral_service.py`
- Test: `tests/test_services.py`

**Interfaces:**
- Produces `normalize_computational_thinking(value) -> list[dict]`, returning one entry for each configured CT practice in the required order.
- Each returned entry has string fields `practice`, `status`, `activity`, `evidence`, `limitation`, and `refinement`.

- [ ] **Step 1: Write failing tests**

Add tests for a complete response, a missing dimension, an unknown status, and preserved evidence/refinement text. Assert the six practice names, stable order, default status `Not identified`, and empty optional fields.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `app\venv\Scripts\python.exe -m unittest tests.test_services.MistralServiceTests -v`

Expected: FAIL because `normalize_computational_thinking` does not exist.

- [ ] **Step 3: Implement minimal normalization**

Implement the function in `mistral_service.py` using a single ordered constant for the six practices. Accept only the three allowed statuses; map missing or unknown values to `Not identified`, coerce non-string content safely, and default missing entries to empty evidence/activity/limitation/refinement fields.

- [ ] **Step 4: Integrate normalization into `call_mistral_analysis`**

After parsing a successful dictionary response, normalize its `computational_thinking` field before returning it. Preserve all existing analysis fields and error responses.

- [ ] **Step 5: Run the focused tests and verify they pass**

Run: `app\venv\Scripts\python.exe -m unittest tests.test_services.MistralServiceTests -v`

Expected: PASS, including the new CT normalization tests.

- [ ] **Step 6: Commit**

```bash
git add app/server/mistral_service.py tests/test_services.py
git commit -m "Add computational thinking response normalization"
```

### Task 2: Extend the analysis prompt with CT rules

**Files:**
- Modify: `app/server/prompts/analysis_system_prompt.txt`
- Test: `tests/test_services.py`

**Interfaces:**
- The existing analysis prompt produces the CT contract consumed by Task 1.

- [ ] **Step 1: Write failing prompt-contract test**

Add a test that reads the prompt file and asserts it names all six practices, all three statuses, the learner-activity evidence rule, the prohibition on keyword/topic/technology-only inference, and the required output keys.

- [ ] **Step 2: Run the test and verify it fails**

Run: `app\venv\Scripts\python.exe -m unittest tests.test_services.MistralServiceTests.test_analysis_prompt_contains_computational_thinking_contract -v`

Expected: FAIL because the prompt does not yet contain the CT contract.

- [ ] **Step 3: Add the CT analysis instructions**

Add a concise section to the existing prompt requiring exactly six CT entries, activity-linked evidence, limitations for weak representation, and goal-aligned refinements only when appropriate. Keep the existing analysis schema and instructions intact.

- [ ] **Step 4: Run the prompt-contract test and the full suite**

Run: `app\venv\Scripts\python.exe -m unittest tests.test_services.MistralServiceTests.test_analysis_prompt_contains_computational_thinking_contract -v`

Then run: `cmd /c run_tests.bat`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/server/prompts/analysis_system_prompt.txt tests/test_services.py
git commit -m "Require evidence-based computational thinking analysis"
```

### Task 3: Render the Step 2 CT feedback panel

**Files:**
- Modify: `app/frontend/first-analysis-and-suggestions.html`

**Interfaces:**
- Consumes `analysis.computational_thinking` normalized by Task 1.
- Produces a `Computational Thinking` panel with a compact overview row for each practice and expandable evidence details.

- [ ] **Step 1: Add the panel shell and styles**

Place the panel below `analysisSections` and before the upload/next-step controls. Add scoped classes for the overview table, expandable details, and the three descriptive status accents without changing the existing analysis table layout.

- [ ] **Step 2: Add rendering helpers**

Implement small browser helpers that safely normalize the six-entry array for display, create text nodes rather than injecting model text as HTML, and render activity, evidence, limitation, and refinement only when supplied.

- [ ] **Step 3: Add expandable rows**

Use native `<details>`/`<summary>` elements or equivalent accessible controls. The collapsed row must show practice, status, and activity; the expanded content must show evidence and optional limitation/refinement.

- [ ] **Step 4: Add the all-not-identified state**

Render the panel even when the response contains only defaults. Do not hide the panel or replace it with a generic empty message.

- [ ] **Step 5: Perform a local UI check**

Start the tutor locally with the existing launcher, open Step 2 using a stored analysis payload containing one item in each status, and verify the panel appears below the existing categories, rows expand, model text is displayed as text, and all six dimensions appear.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/first-analysis-and-suggestions.html
git commit -m "Add computational thinking feedback panel to step two"
```

### Task 4: Full verification and review

**Files:**
- No new files; review all files changed by Tasks 1-3.

- [ ] **Step 1: Run the complete automated suite**

Run: `cmd /c run_tests.bat`

Expected: PASS with zero failures and zero errors.

- [ ] **Step 2: Run syntax and launcher checks**

Run: `app\venv\Scripts\python.exe -m py_compile app/server/mistral_service.py app/server/app.py`

Then run: `cmd /c start_tutor.bat --check`

Expected: both checks pass.

- [ ] **Step 3: Review the diff for requirement compliance**

Confirm the prompt contains the strict learner-activity rule, the backend always returns six dimensions, the UI presents evidence/activity/refinement, and no API key or full secret is added to logs.

- [ ] **Step 4: Commit any verification-only fixes**

Use a focused commit if review finds a real issue; otherwise leave the working tree clean.
