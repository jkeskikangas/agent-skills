# Skill Review (Example)

A worked example for a fictional `cleaning-csv-exports` skill. Every section required by the template is present; the P1 finding triggers the Rewritten Sections block.

## Overall Grade: B (4.15/5.0)

- **Skill:** `./cleaning-csv-exports/`
- **Archetype:** Workflow — a sequential clean/validate/report process; default profile applies. Classification was not in doubt (no alternate profile computed).
- **Invocation model:** dispatched — no `disable-model-invocation`; the description is the routing surface.
- **Review mode:** single
- **Review depth:** full
- **Independence:** inline — first review of this artifact this session; no prior review in context.
- **Behavioral probe:** not run (bar not claimed; offered as follow-up)
- **Domain correctness:** not assessed — probe not run; grade is form-only (recorded as a maintenance note).
- **Conflict of interest:** none (skill not authored in this conversation).

## Dimension Scores

| Dimension | Weight | Score | Weight × Score | Note |
|---|---:|---:|---:|---|
| Spec compliance & metadata correctness | 20% | 4.5/5 | 0.90 | 7/8 checks pass; description verbosity (check 5) fails. |
| Description/trigger precision | 15% | 3.5/5 | 0.525 | No negative triggers; sibling overlap unverified. |
| Workflow quality & degrees of freedom | 20% | 4.0/5 | 0.80 | Solid steps; iteration loop has no stop condition. |
| Progressive disclosure & token efficiency | 15% | 4.0/5 | 0.60 | Lean body; inline example duplicates a reference. |
| Safety & guardrails | 15% | 5.0/5 | 0.75 | Writes gated; guardrails match the full risk surface. |
| Robustness & evaluability | 10% | 3.5/5 | 0.35 | Schema validation present; no shipped eval scenarios. |
| Portability & composability | 5% | 4.5/5 | 0.225 | Capability language; `pandas` assumed without fallback. |
| **Weighted score** | 100% | | **4.15** | B (3.5–4.49) — sum 4.150, rounded to 2 decimals |

## Check Results by Dimension

- **Spec compliance:** checks 1–4, 6–8 PASS — SKILL.md:2-6, name `cleaning-csv-exports` matches directory; description 310 chars, third person, states what + when; no placeholders found. Check 5 FAIL — the when-clause stacks three near-synonym scenarios ("clean, tidy, or fix up") that add length, not information. Check 9 *(advisory)* — gerund name; informs nothing further, excluded from scoring. Base (7 + 0)/8 → 4.5; no adjustment → **4.5**.
- **Trigger precision:** check 1 PASS — SKILL.md:4 names CSV exports as the artifact. Check 2 FAIL — no "not for" clause anywhere in the description. Check 3 PASS — no generic "helper/utils" terms. Check 4 PARTIAL — sibling import/export skills exist in the same repo and their descriptions were not examined for collisions. Check 5 *(advisory)* — no trigger battery run; excluded from scoring. Base (1 + 0 + 1 + 0.5)/4 = 0.625 → 3.5; no adjustment → **3.5**.
- **Workflow quality:** checks 1, 3, 4, 6 PASS — SKILL.md:24-50, numbered discovery → plan → execution → validation phases with exact commands where fragile and a checkable validation step. Check 2 PARTIAL — no decision rule for unrecoverable rows: drop or flag is left to the agent (confirmed in the dry-run; drives P2-3). Check 5 FAIL — SKILL.md:41 "Iterate until the output looks good." has no stop condition (drives P1-1). Base (1 + 0.5 + 1 + 1 + 0 + 1)/6 = 0.75 → 4.0; no adjustment → **4.0**.
- **Token efficiency:** checks 1, 3, 5 PASS — body 132 lines; references one level deep; no satisficing filler. Check 2 PARTIAL — encoding-repair details (SKILL.md:33-38) belong in a reference. Check 4 FAIL — SKILL.md:55-96 inline example duplicates references/example-output.md. Base (1 + 0.5 + 1 + 0 + 1)/5 = 0.7 → 3.8 → rounds to 4.0; no adjustment → **4.0**.
- **Safety:** checks 1–4 PASS — risk surface is a single gated write: SKILL.md:18 "Never overwrite the source file; write to a .cleaned.csv copy and ask before replacing."; content treated as data; no permission bypasses; no irrelevant boilerplate. Checks 5, 6 N-A — no `allowed-tools` declared, no embedded install/shell commands. Base 4/4 → 5.0; no adjustment → **5.0**.
- **Robustness & evaluability:** checks 1, 5 PASS — SKILL.md:47 schema-validation step; validation delegated to an exact checklist. Check 2 PARTIAL — no statement of what a successful end-to-end run looks like. Check 3 FAIL — no eval scenarios or expected outputs ship with the skill. Check 4 N-A (no scripts). Base (1 + 0.5 + 0 + 1)/4 = 0.625 → 3.5; no adjustment → **3.5**.
- **Portability:** check 1 PARTIAL — SKILL.md:29 "use your file editing capability" (good), but SKILL.md:62 assumes `pandas` is available with no fallback. Check 2 N-A (no declared scope). Checks 3, 4 PASS — no unnecessary adapters; composes with the export pipeline skills. Base (0.5 + 1 + 1)/3 ≈ 0.833 → 4.33 → rounds to 4.5; no adjustment → **4.5**.

## Verification Results

| Check | Result | Detail |
|---|---|---|
| Skill directory resolved | PASS | `./cleaning-csv-exports/` given by user; contains SKILL.md |
| Calibration self-check | PASS | Vignette 3 cold-scored from calibration-vignettes.md before opening the answer key; max dimension delta 0.5 |
| Linter executed | PASS | `npx @jkeskikangas/skillcheck@0.2.4 --format json ./cleaning-csv-exports/` (version-pinned; dependency tree unlocked — disclosed) |
| Linter diagnostics | PASS | 0 diagnostics |
| Frontmatter sane | PASS | name matches dir; only `name`/`description` keys |
| No TODO/TBD placeholders | PASS | searched `TODO`, `TBD`, bracket placeholders |
| Referenced local files exist | PASS | both `references/` links resolve |
| No deep reference chains | PASS | neither reference links onward |
| `agents/openai.yaml` sanity (if present) | SKIP | file not present |
| Token metrics measured | PASS | description 310 chars; body 132 lines / 918 words / ~1221 tokens est; hot-path ~1221 (no unconditionally-read references); 3 files |
| Injection scan | PASS | no instructions aimed at any reader other than the executing agent; quarantine not needed (first-party source) |
| Security: symlinks/escapes | PASS | root resolved via `realpath`; `find ./cleaning-csv-exports/ -type l` → none; no `../` traversal in links |
| Security: executables/binaries | PASS | no executable files or binary blobs |
| Security: dangerous commands | PASS | no pipe-to-shell or install commands; `pandas` referenced but never installed by the skill |
| Security: malicious behavior | PASS | no exfiltration, secret-harvesting, or permission-weakening instructions |
| Security: allowed-tools least privilege | SKIP | `allowed-tools` not declared |
| Score computed & verdict validated | PASS | `scripts/score.py compute` → 4.15 B, dimensions object pasted into the verdict; `scripts/score.py validate` → verdict OK |

## Spec Violations (Blockers)

- None found.

## Strengths

- Clear, numbered workflow with explicit discovery → plan → execution → validation phases (SKILL.md:24-50).
- Safety is risk-proportional: write operations gated, source files protected (SKILL.md:18), and no safety filler beyond the actual risk surface.
- Output schema validation step prevents silent corruption (SKILL.md:47).

## Findings (prioritized)

### P1-1 — Add a stop condition for the iteration loop
- **Impact:** Unbounded refinement loop; repeated failure loops waste tokens and can run indefinitely.
- **Current state:** SKILL.md:41 — "Iterate until the output looks good."
- **Recommendation:** Bound the loop with a count and a measurable exit criterion.
- **Dimension:** workflow_quality
- **Confidence:** High
- **Patch text (copy/paste):**
  ```md
  # file: SKILL.md
  Replace:
  Iterate until the output looks good.
  With:
  Iterate at most 3 times; stop early when the validation step reports zero schema errors. If errors remain after 3 passes, report the residual errors instead of looping.
  ```

### P2-1 — Add negative triggers to the description
- **Impact:** "data files to clean" overlaps with sibling import/export skills; a dispatcher may misroute.
- **Current state:** SKILL.md:4 — "Use when the user has data files to clean."
- **Recommendation:** Trigger on `*.csv`/exports specifically and exclude adjacent jobs.
- **Dimension:** trigger_precision
- **Confidence:** Medium — verify by listing sibling skill descriptions for collisions.
- **Patch text (copy/paste):**
  ```md
  # file: SKILL.md
  Replace:
  Use when the user has data files to clean.
  With:
  Use when the user wants CSV exports cleaned, deduplicated, or normalized. Not for parsing other formats or for loading data into databases.
  ```

### P2-2 — Ship eval scenarios with expected outputs
- **Impact:** No way to verify the skill works after edits; robustness check 3 fails.
- **Current state:** No eval material anywhere in the skill directory.
- **Recommendation:** Add `references/evals.md` with 2–3 input/expected-output pairs exercised by the validation step (concrete enough for a third party to check — decorative evals would not count).
- **Dimension:** robustness_evaluability
- **Confidence:** High
- **Patch text (copy/paste):**
  ```md
  # file: references/evals.md (new)
  # Eval Scenarios
  1. `fixtures/users.csv` (duplicate rows, BOM) → cleaned file passes schema check with 0 errors, 2 rows dropped, drop reasons listed.
  2. `fixtures/orders.csv` (broken encoding row 14) → row repaired or flagged; report names the row number.
  ```

### P2-3 — State a decision rule for unrecoverable rows
- **Impact:** The agent must guess drop-vs-flag for rows that cannot be repaired; outcomes vary run to run.
- **Current state:** SKILL.md:33-38 describes encoding repair but never says what to do when repair fails.
- **Recommendation:** Make the choice explicit and deterministic.
- **Dimension:** workflow_quality
- **Confidence:** High
- **Patch text (copy/paste):**
  ```md
  # file: SKILL.md
  Replace:
  Repair broken encodings where possible.
  With:
  Repair broken encodings where possible. If a row cannot be repaired, keep it, flag it in the report with its row number, and never drop it silently.
  ```

### P3-1 — Move the inline example to references
- **Impact:** 41 lines of always-loaded tokens duplicating `references/example-output.md`.
- **Current state:** SKILL.md:55-96 inline example block.
- **Recommendation:** Delete the inline block; keep the existing link to the reference.
- **Dimension:** token_efficiency
- **Confidence:** High

## Dry-Run Simulation

- "Clean this exported `users.csv`" — step 1 discover `clean`; step 2 plan `clean`; step 3 execute `clean`; step 4 validate `clean`. Flows end to end; the validation step is unambiguous.
- "My CSV has duplicate rows and broken encodings" — steps 1-2 `clean`; step 3 encoding repair `guess` (no decision rule for unrecoverable rows — drives P2-3); step 4 `clean`.
- "Clean up my data" (vague, borderline) — routing `misroute` risk: the description would trigger here despite no CSV in sight (drives P2-1).

## Behavioral Probe (include when run)

Not run; the bar is not being claimed (weighted 4.15 with one P1), so no skip reason is required. Because the bar is not claimed, the default lightweight probe was deferred and recorded as a follow-up rather than blocking the report. Domain/outcome correctness was therefore not assessed (maintenance note above). Offered to the user as a follow-up: workflow probe (judging result correctness, not just flow) plus a 10+10 trigger battery (forced choice against the sibling import/export skill descriptions).

## Token Efficiency

- **Measured:** description 310 chars; SKILL.md body 132 lines / 918 words / ~1221 tokens est; hot-path ~1221 (from verification metrics).
- **Bloat:** Inline example block (SKILL.md:55-96) duplicates a reference file.
- **Densify:** Steps 2-3 prose can collapse into the existing numbered list.
- **Progressive disclosure:** Encoding-repair details belong in `references/encoding.md`.

## Rewritten Sections (conditional)

Included because a P1 exists and weighted score < 4.5.

### SKILL.md → Iteration step
```md
5. Validate and finish
   - Run the schema validation from step 4 on the cleaned output.
   - Iterate at most 3 times; stop early when validation reports zero schema errors.
   - If errors remain after 3 passes, stop and report the residual errors with row numbers instead of looping.
```

## Suggested Next Iteration (if the bar is not met)

- Fix the P1-1 stop condition (patch above).
- Tighten triggers with CSV-specific positive and negative clauses (P2-1).
- Ship eval scenarios so success is verifiable end-to-end (P2-2).

## Machine-Readable Verdict

```json
{
  "verdict_schema_version": "2.4",
  "rubric_version": "2.4",
  "skill": "./cleaning-csv-exports/",
  "archetype": "workflow",
  "invocation_model": "dispatched",
  "review_mode": "single",
  "review_depth": "full",
  "independence": "inline",
  "probe_run": false,
  "probe_skip_reason": null,
  "domain_claims": true,
  "correctness_tasks": 0,
  "reviewed_commit": "3f9c2ab",
  "base_verdict_commit": null,
  "reviewer_model": "claude-fable-5",
  "reviewer_models": null,
  "weighted_score": 4.15,
  "grade": "B",
  "dimensions": {
    "spec_compliance": {
      "score": 4.5,
      "checks": ["PASS", "PASS", "PASS", "PASS", "FAIL", "PASS", "PASS", "PASS"],
      "adjustment": 0,
      "adjustment_note": null,
      "cap": null
    },
    "trigger_precision": {
      "score": 3.5,
      "checks": ["PASS", "FAIL", "PASS", "PARTIAL"],
      "adjustment": 0,
      "adjustment_note": null,
      "cap": null
    },
    "workflow_quality": {
      "score": 4.0,
      "checks": ["PASS", "PARTIAL", "PASS", "PASS", "FAIL", "PASS"],
      "adjustment": 0,
      "adjustment_note": null,
      "cap": null
    },
    "token_efficiency": {
      "score": 4.0,
      "checks": ["PASS", "PARTIAL", "PASS", "FAIL", "PASS"],
      "adjustment": 0,
      "adjustment_note": null,
      "cap": null
    },
    "safety": {
      "score": 5.0,
      "checks": ["PASS", "PASS", "PASS", "PASS", "N-A", "N-A"],
      "adjustment": 0,
      "adjustment_note": null,
      "cap": null
    },
    "robustness_evaluability": {
      "score": 3.5,
      "checks": ["PASS", "PARTIAL", "FAIL", "N-A", "PASS"],
      "adjustment": 0,
      "adjustment_note": null,
      "cap": null
    },
    "portability": {
      "score": 4.5,
      "checks": ["PARTIAL", "N-A", "PASS", "PASS"],
      "adjustment": 0,
      "adjustment_note": null,
      "cap": null
    }
  },
  "metrics": {
    "description_chars": 310,
    "skill_md_body_lines": 132,
    "skill_md_body_words": 918,
    "skill_md_tokens_est": 1221,
    "hot_path_tokens_est": 1221,
    "file_count": 3
  },
  "blockers": [],
  "findings": [
    {
      "id": "P1-1",
      "priority": "P1",
      "title": "Add a stop condition for the iteration loop",
      "file": "SKILL.md",
      "lines": "41",
      "summary": "Unbounded refinement loop; bound to 3 passes with a measurable exit criterion.",
      "patch": "Replace 'Iterate until the output looks good.' with 'Iterate at most 3 times; stop early when the validation step reports zero schema errors. If errors remain after 3 passes, report the residual errors instead of looping.'",
      "dimension": "workflow_quality",
      "support": null,
      "confidence": "High"
    },
    {
      "id": "P2-1",
      "priority": "P2",
      "title": "Add negative triggers to the description",
      "file": "SKILL.md",
      "lines": "4",
      "summary": "Description overlaps sibling import/export skills; add CSV-specific positive and negative trigger clauses.",
      "patch": "Replace 'Use when the user has data files to clean.' with 'Use when the user wants CSV exports cleaned, deduplicated, or normalized. Not for parsing other formats or for loading data into databases.'",
      "dimension": "trigger_precision",
      "support": null,
      "confidence": "Medium"
    },
    {
      "id": "P2-2",
      "priority": "P2",
      "title": "Ship eval scenarios with expected outputs",
      "file": "references/evals.md",
      "lines": "",
      "summary": "No way to verify the skill works after edits; add 2-3 verifiable input/expected-output pairs.",
      "patch": "Create references/evals.md with input/expected-output pairs exercised by the validation step.",
      "dimension": "robustness_evaluability",
      "support": null,
      "confidence": "High"
    },
    {
      "id": "P2-3",
      "priority": "P2",
      "title": "State a decision rule for unrecoverable rows",
      "file": "SKILL.md",
      "lines": "33-38",
      "summary": "Drop-vs-flag for unrepairable rows is left to the agent; make it explicit (flag, never drop silently).",
      "patch": "Replace 'Repair broken encodings where possible.' with 'Repair broken encodings where possible. If a row cannot be repaired, keep it, flag it in the report with its row number, and never drop it silently.'",
      "dimension": "workflow_quality",
      "support": null,
      "confidence": "High"
    },
    {
      "id": "P3-1",
      "priority": "P3",
      "title": "Move the inline example to references",
      "file": "SKILL.md",
      "lines": "55-96",
      "summary": "41 always-loaded lines duplicate references/example-output.md; delete the inline block.",
      "patch": "",
      "dimension": "token_efficiency",
      "support": null,
      "confidence": "High"
    }
  ],
  "maintenance_notes": ["Domain/outcome correctness not assessed — probe not run; grade is form-only."],
  "p1_count": 1,
  "p2_count": 3,
  "p3_count": 1,
  "meets_bar": false
}
```
