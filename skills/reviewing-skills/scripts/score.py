#!/usr/bin/env python3
"""Deterministic scorer and verdict validator for reviewing-skills (stdlib only, no deps).

Subcommands:
  compute        <checks.json>            Derive dimension scores, weighted score, and grade
                                          from per-check verdicts. List non-advisory checks
                                          only, in rubric order; per-dimension check counts and
                                          the N-A allowlist are enforced. Flags band-edge
                                          uncertainty and archetype-fragility.
  validate       <verdict.json>           Validate a final machine-readable verdict block
                                          (schema 2.4). Recomputes every dimension score from
                                          its embedded checks (and optional cap) and the
                                          weighted score from the archetype weights. Enforces
                                          the critical-check cap (a FAIL on a *(critical)* check
                                          requires cap <= 3.0), the N-A allowlist (N-A only
                                          where the rubric licenses it, so it cannot shrink the
                                          denominator), the gate-fragility rule (a band-flippable
                                          meets_bar at the 4.5 gate requires ensemble mode), the
                                          archetype-fragility rule (a meets_bar that clears the
                                          gate only under the chosen archetype requires ensemble),
                                          and the domain-correctness gate (a domain-claim skill
                                          needs correctness_tasks >= 3, checked on a probe model
                                          distinct from the scorer (probe_model != reviewer_model)
                                          or with a recorded same_model_probe_reason; rubric
                                          Scoring rules / Dim3 c7).
  validate-fleet <fleet.json>             Validate a batch-mode fleet summary (fleet schema 1.0).
  verify-evidence <verdict.json> <dir>    Re-ground a verdict against the reviewed skill at
                                          <dir>: every finding (cited file exists, line range in
                                          range, quoted "Replace ..." snippet verbatim) AND the
                                          mechanically-checkable defense — Dim1 metadata (name ==
                                          dir, description angle-bracket/length) and metrics
                                          (description_chars) re-derived from SKILL.md.

compute input format ("invocation_model" optional, default "dispatched"; it re-scopes the
Dimension-2 N-A allowlist for user-invoked skills):
  {
    "archetype": "workflow",
    "invocation_model": "dispatched",
    "dimensions": {
      "spec_compliance":        {"checks": ["PASS", ...]},               # 8 verdicts
      "trigger_precision":      {"checks": [...],                        # 4 verdicts
                                 "adjustment": 0.5, "adjustment_note": "...",
                                 "cap": 3.0},                            # optional dimension cap
      "workflow_quality":       {"checks": [...]},                       # 6 verdicts
      "token_efficiency":       {"checks": [...]},                       # 5 verdicts
      "safety":                 {"checks": [...]},                       # 6 verdicts
      "robustness_evaluability":{"checks": [...]},                       # 5 verdicts
      "portability":            {"checks": [...]}                        # 4 verdicts
    }
  }

A dimension's "cap" (1.0-5.0) bounds its final score: final = min(cap, base + adjustment).
A cap is not a holistic adjustment and is exempt from the net-adjustment limit. There are two
sources, composed by min(): (1) the *(critical)*-check cap of 3.0, which `compute` applies and
`validate` enforces automatically from the check verdicts (Dim2 c1, Dim5 c4, Dim6 c2) — the
reviewer no longer has to remember it; (2) a reviewer-supplied cap, e.g. the measured
trigger-battery routing cap on Dimension 2.

compute output includes a paste-ready "dimensions" object for the verdict block, a
"band_stability" report (does any single one-level check flip change the grade band / drop the
score below the 4.5 gate), and an "archetype_robustness" report (the weighted score under all
four profiles, and whether the gate pass hinges on the chosen archetype). A meets_bar claim that
is gate-fragile or archetype-fragile requires ensemble mode.

Exit codes: 0 = OK (warnings go to stderr), 1 = validation failure, 2 = usage or input error.
"""

import json
import os
import re
import sys
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP

DIMENSIONS = [
    "spec_compliance",
    "trigger_precision",
    "workflow_quality",
    "token_efficiency",
    "safety",
    "robustness_evaluability",
    "portability",
]

# Non-advisory checks per dimension, per rubric 2.4. Advisory checks are excluded.
EXPECTED_CHECKS = {
    "spec_compliance": 8,
    "trigger_precision": 4,
    "workflow_quality": 6,
    "token_efficiency": 5,
    "safety": 6,
    "robustness_evaluability": 5,
    "portability": 4,
}

WEIGHTS = {
    "workflow":     [20, 15, 20, 15, 15, 10, 5],
    "reference":    [20, 20, 5, 25, 10, 10, 10],
    "tool-wrapper": [15, 15, 15, 10, 20, 20, 5],
    "orchestrator": [15, 15, 25, 10, 15, 10, 10],
}

VERDICTS = {"PASS", "PARTIAL", "FAIL", "N-A"}
REVIEW_MODES = {"single", "batch", "comparative", "forensic", "ensemble"}
REVIEW_DEPTHS = {"full", "triage", "incremental"}
INVOCATION_MODELS = {"dispatched", "user-invoked", "both"}
INDEPENDENCE = {"fresh-context", "inline"}
CONFIDENCES = {"High", "Medium", "Low"}
GRADES = {"A", "B", "C", "D", "F"}
METRIC_KEYS = (
    "description_chars",
    "skill_md_body_lines",
    "skill_md_body_words",
    "skill_md_tokens_est",
    "hot_path_tokens_est",
    "file_count",
)
SCHEMA_VERSION = "2.4"
RUBRIC_VERSIONS = {"2.4"}
FLEET_SCHEMA_VERSION = "1.0"
NET_ADJUSTMENT_CAP = 0.15   # |sum(weight_i * adj_i)| / 100 must not exceed this
DIMENSION_FLOOR = 3.5       # meets_bar requires every dimension final >= this
GATE = 4.5                  # weighted-score gate for an A / meets_bar
BAND_EDGES = (1.5, 2.5, 3.5, 4.5)   # grade-band boundaries
BAND_EDGE_TOL = 0.05        # within this of a boundary => band-uncertain (informational)
CRITICAL_CAP = 3.0          # a FAIL on a *(critical)* check caps its dimension's final here

# 0-based positions of the *(critical)* checks within each dimension's non-advisory check
# list (rubric 2.4): Dim2 c1 (strong positive trigger), Dim5 c4 (no-bypass / treats content
# as data), Dim6 c2 (success verifiable). The scorer enforces the cap from the check verdicts
# themselves, so it no longer depends on the reviewer remembering to supply `cap`.
CRITICAL = {
    "trigger_precision": (0,),
    "safety": (3,),
    "robustness_evaluability": (1,),
}
ONE_LEVEL = {"PASS": ("PARTIAL",), "PARTIAL": ("PASS", "FAIL"), "FAIL": ("PARTIAL",)}

# Per-dimension N-A allowlist: 0-based indices of checks the rubric grants an explicit
# "N-A if ..." condition. Because base = 1 + 4*(PASS + 0.5*PARTIAL)/applicable and
# applicable = checks - N-A, marking a would-be FAIL as N-A drops it from the denominator and
# inflates the base. The scorer therefore rejects N-A anywhere the rubric does not license it,
# so inapplicability cannot be used as a score lever. Entries that depend on archetype /
# invocation model are layered on in na_allowed().
NA_BASE = {
    "spec_compliance": frozenset(),                # frontmatter/description/placeholders always apply
    "trigger_precision": frozenset({3}),           # c4 collisions: N-A if no siblings are visible
    "workflow_quality": frozenset(),               # a workflow's steps always apply (reference relaxes)
    "token_efficiency": frozenset(),               # density checks always apply
    "safety": frozenset({4, 5}),                   # c5 allowed-tools (if declared), c6 embedded commands
    "robustness_evaluability": frozenset({3, 4}),  # c4 scripts, c5 script-coupled determinism
    "portability": frozenset({1}),                 # c2 declared-scope honored: N-A if none declared
}


def na_allowed(key, archetype, invocation_model):
    """Indices where N-A is legitimate for this dimension under the given archetype /
    invocation model, per the rubric's own 'N-A if ...' conditions. Anything else is rejected."""
    allowed = set(NA_BASE.get(key, ()))
    if key == "trigger_precision" and invocation_model in ("user-invoked", "both"):
        allowed.add(1)                  # re-scoped c2 = argument-hint: N-A if the skill takes no args
    if key == "workflow_quality" and archetype == "reference":
        allowed |= {0, 1, 2, 3, 4, 5}   # a reference/knowledge skill may carry minimal/no workflow
    if key == "robustness_evaluability" and archetype == "reference":
        allowed.add(2)                  # c3 eval material: N-A only for a trivial reference skill
    return allowed


def half_step(x):
    """Round to the nearest 0.5; exact midpoints round half to even (no systematic bias)."""
    return float((Decimal(str(x)) * 2).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN) / 2)


def two_dec(x):
    """Round to two decimals, half up (band edges documented in the rubric)."""
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def band(weighted):
    if weighted >= 4.5:
        return "A"
    if weighted >= 3.5:
        return "B"
    if weighted >= 2.5:
        return "C"
    if weighted >= 1.5:
        return "D"
    return "F"


def band_uncertain(weighted):
    """True when the weighted score sits within BAND_EDGE_TOL of any grade-band boundary."""
    return any(abs(weighted - e) <= BAND_EDGE_TOL + 1e-9 for e in BAND_EDGES)


def critical_cap(key, checks):
    """CRITICAL_CAP if any *(critical)* check in this dimension is FAIL, else None (rubric 2.4).

    Derived from the check verdicts, so a critical FAIL caps the dimension even when the
    reviewer forgot to supply `cap`."""
    return CRITICAL_CAP if any(
        i < len(checks) and checks[i] == "FAIL" for i in CRITICAL.get(key, ())
    ) else None


def effective_cap(supplied, key, checks):
    """Compose the reviewer-supplied cap (routing cap, etc.) with the enforced critical cap."""
    caps = [c for c in (supplied, critical_cap(key, checks)) if c is not None]
    return min(caps) if caps else None


def dim_final(key, checks, adj, supplied_cap):
    """Final score for one dimension: base (half-step) + adjustment, clamped, then capped."""
    na = checks.count("N-A")
    applicable = len(checks) - na
    if applicable == 0:
        return None
    base = half_step(1 + 4 * (checks.count("PASS") + 0.5 * checks.count("PARTIAL")) / applicable)
    final = min(5.0, max(1.0, base + adj))
    ec = effective_cap(supplied_cap, key, checks)
    if ec is not None:
        final = min(final, ec)
    return final


def weighted_from(archetype, dim_checks, dim_adj, dim_cap):
    """Recompute the weighted score from per-dimension checks/adjustments/supplied caps."""
    raw = Decimal("0")
    for key, weight in zip(DIMENSIONS, WEIGHTS[archetype]):
        raw += Decimal(str(weight)) * Decimal(str(
            dim_final(key, dim_checks[key], dim_adj.get(key, 0), dim_cap.get(key))))
    return two_dec(raw / 100)


def band_stability(archetype, dim_checks, dim_adj, dim_cap, weighted):
    """Perturb each applicable check by one level (PASS<->PARTIAL<->FAIL) and recompute.

    Reports whether any single flip changes the grade band, and — for a gate claim — whether
    any single flip drops the weighted score below the 4.5 gate (gate_fragile). Critical caps
    are re-derived per trial, so a flip that clears or trips a critical FAIL is reflected."""
    base_band = band(weighted)
    flips = band_changes = 0
    min_w, max_w = weighted, weighted
    gate_fragile = False
    for key in DIMENSIONS:
        checks = dim_checks[key]
        for i, c in enumerate(checks):
            for nb in ONE_LEVEL.get(c, ()):
                trial = dict(dim_checks)
                trial[key] = checks[:i] + [nb] + checks[i + 1:]
                w = weighted_from(archetype, trial, dim_adj, dim_cap)
                flips += 1
                min_w, max_w = min(min_w, w), max(max_w, w)
                if band(w) != base_band:
                    band_changes += 1
                if weighted >= GATE and w < GATE:
                    gate_fragile = True
    return {
        "flips_tested": flips,
        "flips_that_change_band": band_changes,
        "band_stable": band_changes == 0,
        "gate_fragile": gate_fragile,
        "min_under_one_flip": min_w,
        "max_under_one_flip": max_w,
    }


def archetype_scores(dim_finals):
    """Weighted score under every archetype profile, reusing the same dimension finals — only
    the weights differ, so this is the exact score the skill would get under each classification."""
    out = {}
    for arch, weights in WEIGHTS.items():
        raw = Decimal("0")
        for key, w in zip(DIMENSIONS, weights):
            raw += Decimal(str(w)) * Decimal(str(dim_finals[key]))
        out[arch] = two_dec(raw / 100)
    return out


def archetype_robustness(chosen, dim_finals, weighted):
    """Does a gate pass hinge on the chosen archetype? Dimension finals are archetype-independent
    (only weights change), so the per-dimension floor is too; only the >= GATE weighted test moves.
    archetype_fragile => the chosen profile clears the gate but at least one other would not, i.e.
    the A-grade depends on the classification and deserves a second opinion (ensemble)."""
    scores = archetype_scores(dim_finals)
    others_below = sorted(a for a, s in scores.items() if a != chosen and s < GATE)
    return {
        "scores": scores,
        "chosen": chosen,
        "chosen_is_max": all(scores[chosen] >= s for s in scores.values()),
        "archetype_fragile": weighted >= GATE and bool(others_below),
        "profiles_below_gate": others_below,
    }


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def norm_check(c):
    s = str(c).strip().upper()
    return "N-A" if s in {"NA", "N-A", "N/A"} else s


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        fail(f"cannot read {path}: {e}")
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON: {e}")


def dimension_base(key, raw_checks, errors, archetype=None, invocation_model="dispatched"):
    """Normalize checks, enforce the rubric count and N-A allowlist, and return
    (checks, base, applicable, na). Appends to errors and returns None on failure."""
    if not isinstance(raw_checks, list):
        errors.append(f"{key}: checks must be a list")
        return None
    checks = [norm_check(c) for c in raw_checks]
    bad = [c for c in checks if c not in VERDICTS]
    if bad:
        errors.append(f"{key}: invalid check verdicts {bad} (use PASS/PARTIAL/FAIL/N-A; exclude advisory checks)")
        return None
    expected = EXPECTED_CHECKS[key]
    if len(checks) != expected:
        errors.append(f"{key}: expected {expected} non-advisory check verdicts in rubric order, got {len(checks)} "
                      f"(advisory checks are excluded; never drop or merge scored checks)")
        return None
    allowed = na_allowed(key, archetype, invocation_model)
    bad_na = [i + 1 for i, c in enumerate(checks) if c == "N-A" and i not in allowed]
    if bad_na:
        errors.append(f"{key}: N-A is not licensed at check(s) {bad_na} for archetype "
                      f"{archetype!r}/{invocation_model!r} — these checks have no rubric 'N-A if ...' "
                      "condition; score them PASS/PARTIAL/FAIL or flag a rubric maintenance item "
                      "(N-A shrinks the denominator and would inflate the score)")
        return None
    na = checks.count("N-A")
    applicable = len(checks) - na
    if applicable == 0:
        errors.append(f"{key}: all checks are N-A — at least one applicable check is required to score a dimension")
        return None
    base = half_step(1 + 4 * (checks.count("PASS") + 0.5 * checks.count("PARTIAL")) / applicable)
    return checks, base, applicable, na


def read_adjustment(key, spec, errors):
    """Return (adjustment, note) or None on failure. Accepts legacy "justification" as the note key."""
    adj = spec.get("adjustment", 0)
    if not is_num(adj) or abs(adj) > 0.5:
        errors.append(f"{key}: adjustment must be a number within [-0.5, 0.5]")
        return None
    note = spec.get("adjustment_note", spec.get("justification"))
    if adj and not (isinstance(note, str) and note.strip()):
        errors.append(f"{key}: a non-zero adjustment requires a one-line adjustment_note")
        return None
    return adj, (note if isinstance(note, str) and note.strip() else None)


def read_cap(key, spec, errors):
    """Return (ok, cap): cap is None when absent, else a number in [1.0, 5.0]."""
    cap = spec.get("cap")
    if cap is None:
        return True, None
    if not is_num(cap) or not (1.0 <= cap <= 5.0):
        errors.append(f"{key}: cap must be a number in [1.0, 5.0] or null")
        return False, None
    return True, cap


def compute(path):
    data = load(path)
    archetype = data.get("archetype")
    if archetype not in WEIGHTS:
        fail(f"archetype must be one of {sorted(WEIGHTS)}, got {archetype!r}")
    invocation_model = data.get("invocation_model", "dispatched")
    if invocation_model not in INVOCATION_MODELS:
        fail(f"invocation_model must be one of {sorted(INVOCATION_MODELS)} when provided, "
             f"got {invocation_model!r}")
    dims = data.get("dimensions")
    if not isinstance(dims, dict):
        fail('missing "dimensions" object')
    missing = [d for d in DIMENSIONS if d not in dims]
    if missing:
        fail(f"missing dimensions: {', '.join(missing)}")

    errors, warnings = [], []
    verdict_dims, detail = {}, {}
    all_checks, all_adj, all_cap = {}, {}, {}   # supplied caps, for the stability recompute
    weighted_raw = net_adj_raw = Decimal("0")
    for key, weight in zip(DIMENSIONS, WEIGHTS[archetype]):
        spec = dims[key]
        if not isinstance(spec, dict):
            errors.append(f"{key}: must be an object with a checks list")
            continue
        based = dimension_base(key, spec.get("checks"), errors, archetype, invocation_model)
        adjusted = read_adjustment(key, spec, errors)
        ok_cap, cap = read_cap(key, spec, errors)
        if based is None or adjusted is None or not ok_cap:
            continue
        checks, base, applicable, na = based
        adj, note = adjusted
        eff_cap = effective_cap(cap, key, checks)   # enforced critical cap composed with supplied
        final = min(5.0, max(1.0, base + adj))
        if eff_cap is not None:
            final = min(final, eff_cap)
        if eff_cap is not None and eff_cap != cap:
            warnings.append(f"{key}: a FAIL on a *(critical)* check enforces cap {eff_cap} "
                            "(applied automatically; rubric 2.4)")
        if na > len(checks) / 2:
            warnings.append(f"{key}: {na}/{len(checks)} checks are N-A — flag this dimension as low-signal in the report")
        all_checks[key], all_adj[key], all_cap[key] = checks, adj, cap
        verdict_dims[key] = {"score": final, "checks": checks, "adjustment": adj,
                             "adjustment_note": note, "cap": eff_cap}
        detail[key] = {
            "weight": weight,
            "base": base,
            "cap": eff_cap,
            "final": final,
            "applicable": applicable,
            "na": na,
            "contribution": two_dec(weight * final / 100),
        }
        weighted_raw += Decimal(str(weight)) * Decimal(str(final))
        net_adj_raw += Decimal(str(weight)) * Decimal(str(adj))
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        sys.exit(2)

    net_adj = float(net_adj_raw / 100)
    if abs(net_adj) > NET_ADJUSTMENT_CAP + 1e-9:
        fail(f"net weighted adjustment {net_adj:+.3f} exceeds the ±{NET_ADJUSTMENT_CAP} cap "
             "(adjustments must not be able to move the grade band on their own)")

    weighted = two_dec(weighted_raw / 100)
    uncertain = band_uncertain(weighted)
    stability = band_stability(archetype, all_checks, all_adj, all_cap, weighted)
    if stability["gate_fragile"]:
        warnings.append(f"weighted score {weighted} is gate-fragile: a single one-level check flip "
                        f"drops it to {stability['min_under_one_flip']} (< {GATE}). A meets_bar claim "
                        "requires ensemble mode (validate-enforced).")
    elif uncertain:
        warnings.append(f"weighted score {weighted} is within {BAND_EDGE_TOL} of a grade-band edge "
                        "(band-uncertain) — report the flag, though it does not by itself force ensemble.")
    arch_robust = archetype_robustness(archetype, {k: detail[k]["final"] for k in DIMENSIONS}, weighted)
    if arch_robust["archetype_fragile"]:
        warnings.append(f"weighted score {weighted} is archetype-fragile: it clears the {GATE} gate as "
                        f"{archetype} but not as {', '.join(arch_robust['profiles_below_gate'])} "
                        f"({arch_robust['scores']}). A meets_bar claim requires ensemble mode "
                        "(validate-enforced) so the classification gets a second opinion.")
    result = {
        "archetype": archetype,
        "dimensions": verdict_dims,   # paste-ready for the verdict block
        "detail": detail,
        "net_weighted_adjustment": net_adj,
        "min_dimension_score": min(d["final"] for d in detail.values()),
        "weighted_score": weighted,
        "grade": band(weighted),
        "band_uncertain": uncertain,
        "band_stability": stability,
        "archetype_robustness": arch_robust,
        "warnings": warnings,
    }
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(json.dumps(result, indent=2))


def validate(path):
    v = load(path)
    errors = []

    def need(key, types, allow_none=False):
        if key not in v:
            errors.append(f"missing required field: {key}")
            return None
        val = v[key]
        if val is None:
            if not allow_none:
                errors.append(f"{key} must not be null")
            return None
        if not isinstance(val, types):
            errors.append(f"{key} has wrong type: {type(val).__name__}")
            return None
        return val

    if v.get("verdict_schema_version") != SCHEMA_VERSION:
        errors.append(f'verdict_schema_version must be "{SCHEMA_VERSION}" (this validator supports {SCHEMA_VERSION} only)')
    if need("rubric_version", str) not in RUBRIC_VERSIONS:
        errors.append(f"rubric_version must be one of {sorted(RUBRIC_VERSIONS)}")
    need("skill", str)
    archetype = need("archetype", str)
    if archetype is not None and archetype not in WEIGHTS:
        errors.append(f"archetype must be one of {sorted(WEIGHTS)}")
    invocation_model = need("invocation_model", str)
    if invocation_model not in INVOCATION_MODELS:
        errors.append(f"invocation_model must be one of {sorted(INVOCATION_MODELS)}")
    mode = need("review_mode", str)
    if mode not in REVIEW_MODES:
        errors.append(f"review_mode must be one of {sorted(REVIEW_MODES)}")
    depth = need("review_depth", str)
    if depth not in REVIEW_DEPTHS:
        errors.append(f"review_depth must be one of {sorted(REVIEW_DEPTHS)}")
    if need("independence", str) not in INDEPENDENCE:
        errors.append(f"independence must be one of {sorted(INDEPENDENCE)}")
    probe_run = need("probe_run", bool)
    skip_reason = need("probe_skip_reason", str, allow_none=True)
    # Domain-correctness gate (rubric Scoring rules / Dim3 c7): optional fields, conservative
    # defaults. A domain-claim skill cannot meet the bar without outcome correctness checked
    # over >= 3 tasks, so omitting the fields (domain_claims true / 0 tasks) blocks the bar.
    domain_claims = v.get("domain_claims", True)
    if "domain_claims" in v and not isinstance(domain_claims, bool):
        errors.append("domain_claims must be a boolean (does the skill encode domain/technical claims?)")
        domain_claims = True
    correctness_tasks = v.get("correctness_tasks", 0)
    if "correctness_tasks" in v and (not isinstance(correctness_tasks, int)
                                     or isinstance(correctness_tasks, bool) or correctness_tasks < 0):
        errors.append("correctness_tasks must be a non-negative integer "
                      "(count of probe tasks that judged outcome correctness, not mere unblocking)")
        correctness_tasks = 0
    if isinstance(correctness_tasks, int) and correctness_tasks > 0 and probe_run is False:
        errors.append("correctness_tasks > 0 requires probe_run true — outcome correctness is judged by the probe")
    # Probe-model independence (rubric Scoring rules / Dim3 c7): a same-model correctness probe
    # inherits the scorer's own blind spots, so a domain-claim skill's gate needs the probe run on
    # a model distinct from the scorer (probe_model != reviewer_model) or, when only one model is
    # available, an explicit same_model_probe_reason. Both optional; absent both, independence is
    # unestablished and the bar stays blocked for a domain-claim skill (conservative default).
    probe_model = v.get("probe_model")
    if "probe_model" in v and probe_model is not None and not (
            isinstance(probe_model, str) and probe_model.strip()):
        errors.append("probe_model must be a non-empty model identifier or null")
        probe_model = None
    same_model_reason = v.get("same_model_probe_reason")
    if "same_model_probe_reason" in v and same_model_reason is not None and not (
            isinstance(same_model_reason, str) and same_model_reason.strip()):
        errors.append("same_model_probe_reason must be a non-empty string or null")
        same_model_reason = None
    if isinstance(probe_model, str) and probe_model.strip() and probe_run is False:
        errors.append("probe_model is set but probe_run is false — a recorded probe model implies the probe ran")
    reviewed_commit = need("reviewed_commit", str, allow_none=True)
    base_commit = need("base_verdict_commit", str, allow_none=True)
    reviewer_model = need("reviewer_model", str, allow_none=True)
    reviewer_models = need("reviewer_models", list, allow_none=True)
    if mode == "ensemble":
        if not (isinstance(reviewer_models, list) and len(reviewer_models) >= 3
                and all(isinstance(m, str) and m.strip() for m in reviewer_models)):
            errors.append("ensemble verdicts require reviewer_models: a list of >= 3 model identifiers")
    elif reviewer_models is not None:
        errors.append("reviewer_models must be null outside ensemble mode")
    if depth == "incremental":
        if not (isinstance(base_commit, str) and base_commit.strip()):
            errors.append("incremental verdicts require base_verdict_commit (the prior full review's commit)")
        if not (isinstance(reviewed_commit, str) and reviewed_commit.strip()):
            errors.append("incremental verdicts require reviewed_commit")
    elif base_commit is not None:
        errors.append("base_verdict_commit must be null outside incremental depth")

    dims = need("dimensions", dict) or {}
    extra = set(dims) - set(DIMENSIONS)
    missing = set(DIMENSIONS) - set(dims)
    if extra:
        errors.append(f"unknown dimension keys: {sorted(extra)}")
    if missing:
        errors.append(f"missing dimension keys: {sorted(missing)}")

    metrics = need("metrics", dict) or {}
    for mkey in METRIC_KEYS:
        if mkey not in metrics:
            errors.append(f"metrics.{mkey} is missing")
        elif metrics[mkey] is not None and not isinstance(metrics[mkey], int):
            errors.append(f"metrics.{mkey} must be an integer or null")

    notes = need("maintenance_notes", list)
    if isinstance(notes, list) and not all(isinstance(n, str) and n.strip() for n in notes):
        errors.append("maintenance_notes must contain non-empty strings")

    findings = need("findings", list) or []
    counts = {"P1": 0, "P2": 0, "P3": 0}
    p1_ids, seen_ids = set(), set()
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            errors.append(f"findings[{i}] must be an object")
            continue
        fid, prio = f.get("id", ""), f.get("priority", "")
        if not re.fullmatch(r"P[123]-\d+", str(fid)):
            errors.append(f"findings[{i}].id {fid!r} must match P<1|2|3>-<n>")
        elif not str(fid).startswith(prio + "-"):
            errors.append(f"findings[{i}]: id {fid!r} does not match priority {prio!r}")
        if fid in seen_ids:
            errors.append(f"duplicate finding id {fid!r}")
        seen_ids.add(fid)
        if prio in counts:
            counts[prio] += 1
            if prio == "P1":
                p1_ids.add(fid)
        else:
            errors.append(f"findings[{i}].priority {prio!r} must be P1/P2/P3")
        if f.get("confidence") not in CONFIDENCES:
            errors.append(f"findings[{i}].confidence must be one of {sorted(CONFIDENCES)}")
        if not str(f.get("title", "")).strip():
            errors.append(f"findings[{i}].title must be non-empty")
        if prio in {"P1", "P2"} and not str(f.get("patch", "")).strip():
            errors.append(f"findings[{i}] ({fid}): P1/P2 findings require non-empty patch text")
        dim = f.get("dimension")
        if dim is not None and dim not in DIMENSIONS:
            errors.append(f"findings[{i}].dimension {dim!r} must be a rubric dimension key or null")
        sup = f.get("support")
        if sup is not None and (not isinstance(sup, int) or isinstance(sup, bool) or sup < 1):
            errors.append(f"findings[{i}].support must be a positive integer or null")
        if mode != "ensemble" and sup is not None:
            errors.append(f"findings[{i}].support must be null outside ensemble mode")

    blockers = need("blockers", list)
    for i, b in enumerate(blockers or []):
        if not isinstance(b, dict):
            errors.append(f"blockers[{i}] must be an object with registry_item, summary, and finding_id")
            continue
        ri = b.get("registry_item")
        if not isinstance(ri, int) or isinstance(ri, bool) or not 1 <= ri <= 7:
            errors.append(f"blockers[{i}].registry_item must be an integer 1-7 (the rubric's blocker registry)")
        if not str(b.get("summary", "")).strip():
            errors.append(f"blockers[{i}].summary must be non-empty")
        if b.get("finding_id") not in p1_ids:
            errors.append(f"blockers[{i}].finding_id {b.get('finding_id')!r} must reference an existing P1 finding")

    for prio, key in (("P1", "p1_count"), ("P2", "p2_count"), ("P3", "p3_count")):
        if v.get(key) != counts[prio]:
            errors.append(f"{key}={v.get(key)!r} does not match {counts[prio]} {prio} findings")

    ws, grade = v.get("weighted_score"), v.get("grade")
    meets = v.get("meets_bar")
    if not isinstance(meets, bool):
        errors.append("meets_bar must be a boolean")

    if depth == "triage":
        if ws is not None or grade is not None:
            errors.append("triage verdicts must have null weighted_score and grade")
        if any(dims.get(d) is not None for d in DIMENSIONS if d in dims):
            errors.append("triage verdicts must have null dimension scores")
        if meets is True:
            errors.append("triage verdicts can never set meets_bar true")
    else:  # full or incremental: recompute everything from the embedded checks
        scores = {}
        all_checks, all_adj, all_cap = {}, {}, {}   # supplied caps, for the stability recompute
        weighted_raw = net_adj_raw = Decimal("0")
        weights = WEIGHTS.get(archetype)
        for key, weight in zip(DIMENSIONS, weights or [0] * 7):
            spec = dims.get(key)
            if key in missing:
                continue
            if not isinstance(spec, dict):
                errors.append(f"dimensions.{key} must be an object with score/checks/adjustment in {depth} depth")
                continue
            based = dimension_base(key, spec.get("checks"), errors,
                                   archetype if archetype in WEIGHTS else None, invocation_model)
            adjusted = read_adjustment(key, spec, errors)
            ok_cap, cap = read_cap(key, spec, errors)
            if based is None or adjusted is None or not ok_cap:
                continue
            checks, base, _, _ = based
            adj, _ = adjusted
            ccap = critical_cap(key, checks)
            if ccap is not None and (cap is None or cap > ccap + 1e-9):
                errors.append(f"dimensions.{key}: a FAIL on a *(critical)* check requires cap <= {ccap} "
                              f"in the verdict (got {cap!r}); the critical-check cap is not optional (rubric 2.4)")
            eff_cap = effective_cap(cap, key, checks)
            expected_final = min(5.0, max(1.0, base + adj))
            if eff_cap is not None:
                expected_final = min(expected_final, eff_cap)
            score = spec.get("score")
            if not is_num(score):
                errors.append(f"dimensions.{key}.score must be a number")
            elif abs(score - expected_final) > 1e-9:
                errors.append(f"dimensions.{key}.score {score} does not match its checks: base {base} "
                              f"with adjustment {adj:+g}"
                              f"{f', capped at {eff_cap}' if eff_cap is not None else ''} -> {expected_final}")
            else:
                scores[key] = score
                all_checks[key], all_adj[key], all_cap[key] = checks, adj, cap
                if weights:
                    weighted_raw += Decimal(str(weight)) * Decimal(str(score))
                    net_adj_raw += Decimal(str(weight)) * Decimal(str(adj))
        if weights and len(scores) == len(DIMENSIONS):
            net_adj = float(net_adj_raw / 100)
            if abs(net_adj) > NET_ADJUSTMENT_CAP + 1e-9:
                errors.append(f"net weighted adjustment {net_adj:+.3f} exceeds the ±{NET_ADJUSTMENT_CAP} cap")
            expected_ws = two_dec(weighted_raw / 100)
            if not is_num(ws):
                errors.append("weighted_score must be a number in [1.0, 5.0]")
            elif abs(ws - expected_ws) > 1e-9:
                errors.append(f"weighted_score {ws} does not match the dimension scores under the "
                              f"{archetype} profile (expected {expected_ws})")
            elif grade != band(ws):
                errors.append(f"grade {grade!r} does not match weighted_score {ws} (expected {band(ws)!r})")
            if depth == "incremental" and meets is True:
                errors.append("incremental verdicts can never set meets_bar true — gates require a fresh full review")
            if depth == "full" and is_num(ws) and isinstance(meets, bool):
                probe_ok = bool(probe_run) or bool(skip_reason and str(skip_reason).strip())
                model_independent = (
                    isinstance(probe_model, str) and probe_model.strip()
                    and isinstance(reviewer_model, str) and reviewer_model.strip()
                    and probe_model.strip() != reviewer_model.strip()
                ) or bool(isinstance(same_model_reason, str) and same_model_reason.strip())
                correctness_ok = (not domain_claims) or (
                    isinstance(correctness_tasks, int) and correctness_tasks >= 3
                    and model_independent)
                expected = (ws >= GATE and counts["P1"] == 0 and not blockers
                            and min(scores.values()) >= DIMENSION_FLOOR and probe_ok and correctness_ok)
                if expected and len(scores) == len(DIMENSIONS):
                    stab = band_stability(archetype, all_checks, all_adj, all_cap, ws)
                    if stab["gate_fragile"] and mode != "ensemble":
                        errors.append(
                            f"meets_bar at a gate-fragile weighted_score ({ws}: a single one-level check flip "
                            f"drops it to {stab['min_under_one_flip']} < {GATE}) requires ensemble mode "
                            "(3 independent reviews); run an ensemble or do not claim the bar")
                        expected = False
                    arch_rob = archetype_robustness(archetype, scores, ws)
                    if arch_rob["archetype_fragile"] and mode != "ensemble":
                        errors.append(
                            f"meets_bar at an archetype-fragile weighted_score ({ws}: clears {GATE} as "
                            f"{archetype} but not as {', '.join(arch_rob['profiles_below_gate'])}) requires "
                            "ensemble mode (a second opinion on the classification); run an ensemble or "
                            "do not claim the bar")
                        expected = False
                if meets != expected:
                    errors.append(
                        f"meets_bar={meets} is inconsistent (weighted_score {ws}, p1_count {counts['P1']}, "
                        f"blockers {len(blockers or [])}, min dimension {min(scores.values())} vs floor "
                        f"{DIMENSION_FLOOR}, probe_run {probe_run} / skip_reason "
                        f"{'set' if skip_reason else 'null'}, domain_claims {domain_claims} / "
                        f"correctness_tasks {correctness_tasks} (>= 3 required for domain-claim skills), "
                        f"probe_model {probe_model!r} vs reviewer_model {reviewer_model!r} / "
                        f"same_model_probe_reason {'set' if same_model_reason else 'null'} "
                        f"(a domain-claim gate needs a distinct probe model or a recorded reason) "
                        f"-> expected {expected})")

    if errors:
        for e in errors:
            print(f"invalid: {e}", file=sys.stderr)
        sys.exit(1)
    print("verdict OK")


def validate_fleet(path):
    v = load(path)
    errors = []
    if v.get("fleet_schema_version") != FLEET_SCHEMA_VERSION:
        errors.append(f'fleet_schema_version must be "{FLEET_SCHEMA_VERSION}"')
    skills = v.get("skills")
    if not isinstance(skills, list) or not skills:
        errors.append("skills must be a non-empty list")
        skills = []
    for i, s in enumerate(skills):
        if not isinstance(s, dict):
            errors.append(f"skills[{i}] must be an object")
            continue
        if not str(s.get("skill", "")).strip():
            errors.append(f"skills[{i}].skill must be a non-empty path")
        ws, grade = s.get("weighted_score"), s.get("grade")
        if not is_num(ws) or not 1.0 <= ws <= 5.0:
            errors.append(f"skills[{i}].weighted_score must be a number in [1.0, 5.0]")
        elif grade != band(ws):
            errors.append(f"skills[{i}].grade {grade!r} does not match weighted_score {ws} (expected {band(ws)!r})")
        p1 = s.get("p1_count")
        if not isinstance(p1, int) or isinstance(p1, bool) or p1 < 0:
            errors.append(f"skills[{i}].p1_count must be a non-negative integer")
        meets = s.get("meets_bar")
        if not isinstance(meets, bool):
            errors.append(f"skills[{i}].meets_bar must be a boolean")
        elif meets and is_num(ws) and isinstance(p1, int) and (ws < 4.5 or p1 > 0):
            errors.append(f"skills[{i}].meets_bar=true contradicts weighted_score {ws} / p1_count {p1}")
    for key in ("trigger_collisions", "shared_boilerplate"):
        if not isinstance(v.get(key), list):
            errors.append(f"{key} must be a list")
    if errors:
        for e in errors:
            print(f"invalid: {e}", file=sys.stderr)
        sys.exit(1)
    print("fleet OK")


def extract_replace_snippet(patch):
    """Pull the quoted snippet from a 'Replace <X> with <Y>' finding patch, if present."""
    if not isinstance(patch, str):
        return None
    m = re.search(r"[Rr]eplace[:\s]+['\"](.+?)['\"]\s+[Ww]ith", patch, re.S)
    if m:
        return m.group(1).strip()
    # Structured form: "Replace:\n<snippet>\nWith:\n..."
    m = re.search(r"[Rr]eplace:\s*\n(.+?)\n\s*[Ww]ith:", patch, re.S)
    return m.group(1).strip() if m else None


def parse_frontmatter(text):
    """Extract the YAML frontmatter and its simple scalar keys without a YAML dependency.

    Returns (has_frontmatter, fields, single_line): fields maps top-level scalar keys to their
    value (None for a block scalar we cannot reconstruct); single_line is the set of keys that
    parsed as a clean one-line scalar, so callers never measure a value they could not rebuild."""
    if not text.startswith("---"):
        return False, {}, set()
    rows = text.split("\n")
    end = next((i for i in range(1, len(rows)) if rows[i].strip() == "---"), None)
    if end is None:
        return False, {}, set()
    fields, single_line = {}, set()
    for ln in rows[1:end]:
        m = re.match(r"([A-Za-z0-9_-]+):\s*(.*)$", ln)   # leading-space (nested) lines won't match
        if not m or m.group(1) in fields:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val and val[0] in "|>":              # block scalar — not reconstructable here
            fields[key] = None
            continue
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        fields[key] = val
        single_line.add(key)
    return True, fields, single_line


def verify_evidence(verdict_path, skill_dir):
    """Re-ground a verdict against the reviewed skill on disk: every finding's citation (the
    prosecution) AND the mechanically-checkable Dimension-1 / metrics PASS claims (the defense),
    so a clean metadata verdict cannot be asserted against a skill that contradicts it."""
    v = load(verdict_path)
    if not os.path.isdir(skill_dir):
        fail(f"not a directory: {skill_dir}")
    findings = v.get("findings")
    if not isinstance(findings, list):
        fail('verdict has no "findings" array')
    problems, checked = [], 0
    for f in findings if isinstance(findings, list) else []:
        if not isinstance(f, dict):
            continue
        fid = f.get("id", "?")
        rel = str(f.get("file", "")).strip()
        lr = str(f.get("lines", "")).strip()
        if not rel:
            continue
        path = os.path.join(skill_dir, rel)
        if not os.path.isfile(path):
            # A finding that recommends creating a new file has no cited lines — not an error.
            if lr:
                problems.append(f"{fid}: cited file {rel!r} not found under {skill_dir}")
            continue
        checked += 1
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        lines = text.splitlines()
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", lr)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
            if lo < 1 or hi < lo or hi > len(lines):
                problems.append(f"{fid}: cited lines {lr} out of range ({rel} has {len(lines)} lines)")
        snip = extract_replace_snippet(f.get("patch", ""))
        if snip and snip not in text:
            problems.append(f"{fid}: patch 'Replace' snippet not found verbatim in {rel}: {snip[:60]!r}")

    # Ground the defense: re-derive the mechanically-checkable PASS claims (Dim1 metadata +
    # metrics) from disk. Subjective PASSes (workflow shape, density judgments) stay reviewer
    # judgment — no deterministic tool can ground those, and pretending otherwise is theater.
    grounded = []
    spec_checks = (((v.get("dimensions") or {}).get("spec_compliance") or {}).get("checks") or [])
    metrics = v.get("metrics") or {}
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        problems.append(f"metadata: SKILL.md not found under {skill_dir}")
    else:
        with open(skill_md, encoding="utf-8", errors="replace") as fh:
            md = fh.read()
        has_fm, fm, single = parse_frontmatter(md)
        dir_name = os.path.basename(os.path.abspath(skill_dir))
        if not has_fm:
            problems.append("metadata: SKILL.md has no '---' YAML frontmatter block")
        else:
            name = fm.get("name")
            if isinstance(name, str):
                grounded.append("name")
                if name != dir_name:               # Dim1 c2 is checks[1]
                    msg = f"frontmatter name {name!r} != directory {dir_name!r}"
                    problems.append(f"spec_compliance c2 marked PASS but {msg}"
                                    if len(spec_checks) > 1 and spec_checks[1] == "PASS"
                                    else f"metadata: {msg}")
            desc = fm.get("description")
            if isinstance(desc, str) and "description" in single:
                grounded.append("description")
                if "<" in desc or ">" in desc:     # Dim1 c3 forbids angle brackets
                    problems.append("spec_compliance c3 marked PASS but description contains angle brackets"
                                    if len(spec_checks) > 2 and spec_checks[2] == "PASS"
                                    else "metadata: description contains angle brackets")
                if len(desc) > 1024:
                    problems.append(f"metadata: description is {len(desc)} chars (> 1024 limit)")
                dc = metrics.get("description_chars")
                if isinstance(dc, int) and not isinstance(dc, bool) and dc != len(desc):
                    problems.append(f"metrics.description_chars {dc} != measured {len(desc)}")

    if problems:
        for p in problems:
            print(f"unverified: {p}", file=sys.stderr)
        sys.exit(1)
    print(f"evidence OK ({checked} finding(s) + {len(grounded)} metadata fact(s) "
          f"grounded against {skill_dir})")


def main():
    one_arg = {"compute": compute, "validate": validate, "validate-fleet": validate_fleet}
    argv = sys.argv[1:]
    if argv and argv[0] in one_arg and len(argv) == 2:
        one_arg[argv[0]](argv[1])
    elif argv and argv[0] == "verify-evidence" and len(argv) == 3:
        verify_evidence(argv[1], argv[2])
    else:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
