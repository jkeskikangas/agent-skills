# Skill Review

Budget: keep a single full review under ~350 lines excluding the JSON verdict — cut repetition before cutting evidence.

## Overall Grade: [A/B/C/D/F] ([weighted score]/5.0)

- **Skill:** `[path]`
- **Archetype:** [Workflow / Reference / Tool-wrapper / Orchestrator] — [1 line justifying the classification; if classification was uncertain, name the runner-up profile and whether the grade flips under it]
- **Invocation model:** [dispatched / user-invoked / both — Dimension 2 re-scopes for user-invoked]
- **Review mode:** [single / batch / comparative / forensic / ensemble]
- **Review depth:** [full / triage / incremental — see SKILL.md "Review depth"]
- **Independence:** [fresh-context / inline — on repeat or self reviews, inline requires a contamination caveat here]
- **Behavioral probe:** [not run (+ skip reason when claiming the bar) / run — note whether it judged outcome correctness]
- **Domain correctness:** [assessed via probe / not assessed — grade is form-only (record a maintenance note) / N-A (skill encodes no domain claims)]
- **Conflict of interest:** [none / "authored or edited earlier in this conversation — fresh-context review recommended"]

## Dimension Scores

Weights come from the archetype profile in the rubric — copy them; do not invent weights. Derive each score from its check results (next section) via `scripts/score.py compute` (rubric formula as manual fallback); note any holistic adjustment **or cap** in the Note column (a FAIL on a *(critical)* check caps the dimension at 3.0 — the scorer applies this automatically and `validate` requires it; a trigger battery caps Dimension 2; net adjustment effect is capped at ±0.15, caps are exempt). If `compute` reports `gate_fragile` (a single check flip would drop the score below 4.5) or `archetype_fragile` (the score clears 4.5 only under the chosen archetype — see `archetype_robustness`), say so here and escalate to ensemble before claiming the bar; report `band_uncertain` too when set.

| Dimension | Weight | Score | Weight × Score | Note |
|---|---:|---:|---:|---|
| Spec compliance & metadata correctness | [w]% | X/5 | [w×s] | [1 line] |
| Description/trigger precision | [w]% | X/5 | [w×s] | [1 line] |
| Workflow quality & degrees of freedom | [w]% | X/5 | [w×s] | [1 line] |
| Progressive disclosure & token efficiency | [w]% | X/5 | [w×s] | [1 line] |
| Safety & guardrails | [w]% | X/5 | [w×s] | [1 line] |
| Robustness & evaluability | [w]% | X/5 | [w×s] | [1 line] |
| Portability & composability | [w]% | X/5 | [w×s] | [1 line] |
| **Weighted score** | 100% | | **[sum, rounded to 2 decimals]** | [grade band] |

## Check Results by Dimension

Per dimension: grade every rubric check PASS/PARTIAL/FAIL/N-A. Group clean PASSes into one line with one representative evidence cite; list every PARTIAL/FAIL/N-A individually with evidence (`file:line — "short quote"`, or the absence you looked for). Close each dimension with `base → final` and a one-line justification for any holistic adjustment. A verdict without evidence is invalid. Advisory checks: mention them only when they generated findings; never record them as N-A and never feed them to the scorer.

- **Spec compliance:** [check verdicts + evidence; base → final]
- **Trigger precision:** [check verdicts + evidence; base → final]
- **Workflow quality:** [check verdicts + evidence; base → final]
- **Token efficiency:** [check verdicts + evidence; base → final]
- **Safety:** [check verdicts + evidence; base → final]
- **Robustness & evaluability:** [check verdicts + evidence; base → final]
- **Portability:** [check verdicts + evidence; base → final]

## Verification Results

| Check | Result | Detail |
|---|---|---|
| Skill directory resolved | [PASS/FAIL] | [path + how resolved] |
| Calibration self-check | [PASS/FAIL/SKIP] | [vignette cold-scored from calibration-vignettes.md before opening the answer key + max dimension delta, or "calibrated earlier this session"] |
| Linter executed | [PASS/SKIP] | [exact command + version, or why skipped + manual fallback] |
| Linter diagnostics | [PASS/FAIL/SKIP] | [zero diagnostics, or the list] |
| Frontmatter sane | [PASS/FAIL/SKIP] | [name matches dir; required keys; unrecognized keys noted] |
| No TODO/TBD placeholders | [PASS/FAIL/SKIP] | [what you searched for] |
| Referenced local files exist | [PASS/FAIL/SKIP] | [broken links or "none"] |
| No deep reference chains | [PASS/FAIL/SKIP] | [what you checked] |
| `agents/openai.yaml` sanity (if present) | [PASS/FAIL/SKIP] | [interface display_name / short_description / default_prompt present] |
| Token metrics measured | [PASS/SKIP] | [description chars; body lines + words; tokens est; hot-path est; file count] |
| Injection scan | [PASS/FAIL] | [no instructions aimed at any reader other than the executing agent; quarantine used or not] |
| Security: symlinks/escapes | [PASS/FAIL/SKIP] | [skill root resolved via realpath; command used; what was found] |
| Security: executables/binaries | [PASS/FAIL/SKIP] | [unexpected executables or blobs, or "none"] |
| Security: dangerous commands | [PASS/FAIL/SKIP] | [pipe-to-shell / unpinned installs found, or "none"] |
| Security: malicious behavior | [PASS/FAIL/SKIP] | [exfiltration / secret-harvesting / permission-weakening instructions, or "none"] |
| Security: allowed-tools least privilege | [PASS/FAIL/SKIP] | [requested vs needed, or "not declared"] |
| Score computed & verdict validated | [PASS/FAIL/SKIP] | [`scripts/score.py compute` (dimensions pasted into the verdict) + `validate` output, or manual fallback noted] |
| Evidence re-grounded (`verify-evidence`) | [PASS/FAIL/SKIP] | [findings citations + Dim1 metadata/`description_chars` re-derived from `SKILL.md`; required to pass before claiming the bar] |

## Spec Violations (Blockers)

- [List hard violations — every blocker also appears as a P1 finding below and fails the bar regardless of score. If none: "None found".]

## Strengths

- [3–6 bullets with specific references to sections/files]

## Findings (prioritized)

Number findings `P1-1`, `P2-1`, `P3-1`, … — the JSON verdict reuses these ids.

### [P1-1] — [Title]
- **Impact:** [what breaks / token waste / safety risk]
- **Current state:** [what the skill says/does now, with file:line]
- **Recommendation:** [specific change]
- **Dimension:** [rubric dimension key, e.g., workflow_quality]
- **Confidence:** [High / Medium / Low — if not High, state what would verify it]
- **Patch text (copy/paste):**
  ```md
  # file: <relative/path/to/file>
  Replace:
  <exact snippet>
  With:
  <exact replacement>
  ```

[Repeat; max ~15 findings total]

## Dry-Run Simulation

[2–3 representative requests within the skill's trigger scope (include one borderline case). For each, a compact trace: the workflow steps the request exercises, each marked `clean`, `stall`, `guess`, or `misroute`, with a one-line note — cross-reference the findings every non-clean marker produced.]

## Behavioral Probe (include when run)

- **Workflow probe:** [task given to the fresh-context subagent; where it flowed, stalled, guessed, or misrouted; scripts not executed unless the user opted in]
- **Trigger battery:** [gate: 10 in-scope + 10 out-of-scope prompts, accuracy N/20 (≥18/20 = pass); short battery: 5+5, N/10 (≥9/10 = pass) — note the wider uncertainty; forced choice among sibling descriptions when siblings are visible; misroutes cross-referenced to findings]

## Diff Analysis (forensic mode, optional)

Include only if the user requests a diff-centric review (or if a finding is primarily driven by recent changes). Incremental-depth reviews reuse this structure scoped to the diff since `base_verdict_commit`.

- **Base branch used:** `[main/master/<other>]` (state how you chose)
- **Scope:** `<skill>/` (use `git diff --stat` first to scope; `git log --follow` for renamed files)

For each meaningful hunk:
- Quote context using `+/-` prefixed lines.
- Classify: improvement / regression / neutral.
- Note spec/anti-pattern implications (if any).

## Token Efficiency

- **Measured:** [description chars; SKILL.md body lines / words / tokens est; hot-path est — from the verification metrics]
- **Bloat:** [what to delete or move — include rubric-satisficing filler]
- **Densify:** [where to replace prose with bullets/tables]
- **Progressive disclosure:** [what belongs in references/scripts]

## Rewritten Sections (conditional)

Include only when weighted score < 4.5, any P1 exists, or the author requests a rewrite. Rewrite the smallest section(s) needed to clear P1/P2 findings; preserve the author's voice and format.

### [file → section]
```md
[full replacement text]
```

## Suggested Next Iteration (if the bar is not met)

- [Top 3 actions to reach the bar (rubric "Quality bar": weighted ≥ 4.5, no P1s, no blockers, every dimension ≥ 3.5, probe run or skip justified); omit this section if the bar is already met]

## Machine-Readable Verdict

Always end the report with this fenced JSON block (consumed by generator↔critic automation):

```json
{
  "verdict_schema_version": "2.4",
  "rubric_version": "2.4",
  "skill": "[path]",
  "archetype": "workflow|reference|tool-wrapper|orchestrator",
  "invocation_model": "dispatched|user-invoked|both",
  "review_mode": "single|batch|comparative|forensic|ensemble",
  "review_depth": "full|triage|incremental",
  "independence": "fresh-context|inline",
  "probe_run": false,
  "probe_skip_reason": null,
  "domain_claims": true,
  "correctness_tasks": 0,
  "probe_model": null,
  "same_model_probe_reason": null,
  "reviewed_commit": null,
  "base_verdict_commit": null,
  "reviewer_model": null,
  "reviewer_models": null,
  "weighted_score": null,
  "grade": "A|B|C|D|F",
  "dimensions": {
    "spec_compliance": {"score": null, "checks": [], "adjustment": 0, "adjustment_note": null, "cap": null},
    "trigger_precision": {"score": null, "checks": [], "adjustment": 0, "adjustment_note": null, "cap": null},
    "workflow_quality": {"score": null, "checks": [], "adjustment": 0, "adjustment_note": null, "cap": null},
    "token_efficiency": {"score": null, "checks": [], "adjustment": 0, "adjustment_note": null, "cap": null},
    "safety": {"score": null, "checks": [], "adjustment": 0, "adjustment_note": null, "cap": null},
    "robustness_evaluability": {"score": null, "checks": [], "adjustment": 0, "adjustment_note": null, "cap": null},
    "portability": {"score": null, "checks": [], "adjustment": 0, "adjustment_note": null, "cap": null}
  },
  "metrics": {
    "description_chars": null,
    "skill_md_body_lines": null,
    "skill_md_body_words": null,
    "skill_md_tokens_est": null,
    "hot_path_tokens_est": null,
    "file_count": null
  },
  "blockers": [],
  "findings": [
    {
      "id": "P1-1",
      "priority": "P1",
      "title": "",
      "file": "",
      "lines": "",
      "summary": "",
      "patch": "",
      "dimension": null,
      "support": null,
      "confidence": "High|Medium|Low"
    }
  ],
  "maintenance_notes": [],
  "p1_count": 0,
  "p2_count": 0,
  "p3_count": 0,
  "meets_bar": false
}
```

- Scores use the rubric scale 1.0–5.0; the `null`s above are placeholders to fill in a full review, never valid full-review output. Paste the `dimensions` object straight from `scripts/score.py compute` — each entry embeds the non-advisory check verdicts in rubric order, the holistic `adjustment`, its `adjustment_note`, and the dimension `cap` (null when none; otherwise the critical-check or routing cap), so the validator can recompute every score. In triage depth, `weighted_score`, `grade`, and every `dimensions` value stay null and `meets_bar` stays false.
- `reviewed_commit`: short hash of the last commit touching the skill (`git log -1 --format=%h -- <skill>`), with `-dirty` appended when `git status --porcelain -- <skill>` is non-empty, or null outside git — lets loop automation tell skill changes from reviewer drift. Incremental depth requires a clean (non-`-dirty`) `base_verdict_commit`; against a dirty prior verdict, fall back to a full review. `base_verdict_commit`: only in incremental depth — the commit the prior full review scored; null otherwise. `reviewer_model`: the model identifier the reviewer runs as, or null if unknown. `reviewer_models`: the ensemble jury (≥3 entries, ideally heterogeneous); null outside ensemble mode.
- `probe_skip_reason`: required (non-null, one line) whenever `meets_bar` is true with `probe_run` false; null otherwise unless explaining a skip.
- `domain_claims` / `correctness_tasks`: `domain_claims` is true when the skill encodes domain/technical claims (most do); `correctness_tasks` counts the probe tasks that judged **outcome correctness** (not mere unblocking). For a domain-claim skill, `validate` requires `correctness_tasks >= 3` before `meets_bar` can be true (rubric Scoring rules / Dimension 3 c7). Set `domain_claims: false` only for a skill that makes no domain claims. Both are optional and default to `true` / `0` — omitting them conservatively blocks the bar until correctness is recorded. `correctness_tasks > 0` requires `probe_run: true`.
- `probe_model` / `same_model_probe_reason`: a same-model correctness probe inherits the scorer's blind spots, so a domain-claim skill's bar additionally needs the probe run on a model **distinct from the scorer**. Record the probe's model in `probe_model`; `validate` requires `probe_model != reviewer_model`, or a one-line `same_model_probe_reason` when only one model is available. Both optional and default null — absent both, independence is unestablished and the bar stays blocked for a domain-claim skill. A set `probe_model` requires `probe_run: true`.
- `blockers` entries are objects: `registry_item` (1–7, the rubric's blocker registry), `summary`, and `finding_id` of the companion P1 finding.
- `findings` embeds every reported finding (`patch` may be empty for P3s; `lines` is a string like "41" or "55-96"); the `p*_count` fields are derived from it. `dimension` names the rubric dimension a finding maps to (or null); `support` is the number of ensemble reviews that reported the finding (must be null outside ensemble mode).
- `maintenance_notes`: rubric/spec staleness observed during the review (e.g., a platform key the rubric does not know), for the skill maintainer.
- `meets_bar` follows the rubric's canonical Quality bar: full depth, `weighted_score >= 4.5`, `p1_count == 0`, empty `blockers`, every dimension score ≥ 3.5, probe run or skip reason recorded, **and — for a domain-claim skill (`domain_claims: true`) — outcome correctness checked over ≥3 tasks (`correctness_tasks >= 3`) on a probe model distinct from the scorer (`probe_model != reviewer_model`, or a recorded `same_model_probe_reason`), which `validate` enforces** — and — when the score is gate-fragile (a single check flip drops it below 4.5) — ensemble mode.
- Validate the finished block with `python3 scripts/score.py validate <verdict.json>` before delivering (batch fleet summaries: `validate-fleet`). An informative JSON Schema ships at `references/verdict.schema.json`; the script is canonical.
