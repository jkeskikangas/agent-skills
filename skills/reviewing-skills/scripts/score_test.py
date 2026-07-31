#!/usr/bin/env python3
"""Tests for score.py (stdlib unittest, no deps). Run: python3 scripts/score_test.py

Covers the canonical calibration vignettes, the band-edge / banding rules, the enforced
critical-check caps (rubric 2.4), band-stability / gate-fragility, the non-compensatory
floor, the net-adjustment cap, triage/incremental null constraints, and a round-trip of the
shipped worked example. This is the automated regression net the rubric's manual cold-score
protocol previously stood in for."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCORE = os.path.join(HERE, "score.py")
SKILL_DIR = os.path.dirname(HERE)
EXAMPLE = os.path.join(SKILL_DIR, "references", "example-review.md")

spec = importlib.util.spec_from_file_location("score", SCORE)
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)

LEN = dict(zip(score.DIMENSIONS, (8, 4, 6, 5, 6, 5, 4)))
METRICS = {k: 1 for k in score.METRIC_KEYS}


def run(cmd, payload):
    """Run a score.py subcommand on a JSON payload; return (rc, stdout, stderr)."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(payload, f)
        path = f.name
    try:
        r = subprocess.run([sys.executable, SCORE, cmd, path], capture_output=True, text=True)
    finally:
        os.unlink(path)
    return r.returncode, r.stdout, r.stderr


def compute(archetype, checks_by_dim, extra=None, invocation_model=None):
    dims = {k: {"checks": checks_by_dim[k]} for k in score.DIMENSIONS}
    for k, ov in (extra or {}).items():
        dims[k].update(ov)
    payload = {"archetype": archetype, "dimensions": dims}
    if invocation_model is not None:
        payload["invocation_model"] = invocation_model
    rc, out, err = run("compute", payload)
    assert rc == 0, f"compute failed: {err}"
    return json.loads(out)


def run_compute_raw(archetype, checks_by_dim, invocation_model=None):
    """compute without the rc==0 assertion, for rejection tests. Returns (rc, out, err)."""
    dims = {k: {"checks": checks_by_dim[k]} for k in score.DIMENSIONS}
    payload = {"archetype": archetype, "dimensions": dims}
    if invocation_model is not None:
        payload["invocation_model"] = invocation_model
    return run("compute", payload)


def allpass():
    return {k: ["PASS"] * LEN[k] for k in score.DIMENSIONS}


def verdict_from(comp, *, archetype="workflow", mode="single", depth="full",
                 meets=False, probe_run=True, **over):
    v = {
        "verdict_schema_version": score.SCHEMA_VERSION,
        "rubric_version": sorted(score.RUBRIC_VERSIONS)[-1],
        "skill": "./x/", "archetype": archetype, "invocation_model": "dispatched",
        "review_mode": mode, "review_depth": depth, "independence": "inline",
        "probe_run": probe_run, "probe_skip_reason": None,
        "domain_claims": True, "correctness_tasks": 3,
        "probe_model": ("probe-m" if probe_run else None), "same_model_probe_reason": None,
        "reviewed_commit": "abc", "base_verdict_commit": None,
        "reviewer_model": "m", "reviewer_models": (["a", "b", "c"] if mode == "ensemble" else None),
        "weighted_score": comp["weighted_score"], "grade": comp["grade"],
        "dimensions": comp["dimensions"], "metrics": dict(METRICS),
        "blockers": [], "findings": [], "maintenance_notes": [],
        "p1_count": 0, "p2_count": 0, "p3_count": 0, "meets_bar": meets,
    }
    v.update(over)
    return v


# --- Canonical calibration data (calibration-answers.md) ---------------------------------
VIGNETTE_SCORES = {
    "V1": ("workflow", [5.0, 5.0, 4.5, 5.0, 5.0, 4.5, 4.5], 4.83, "A"),
    "V2": ("tool-wrapper", [4.5, 4.0, 4.0, 4.5, 4.0, 3.0, 4.5], 3.95, "B"),
    "V3": ("workflow", [4.0, 3.0, 3.5, 3.0, 3.5, 2.5, 3.5], 3.35, "C"),
    "V4": ("workflow", [2.0, 1.5, 1.5, 2.5, 2.0, 1.5, 2.5], 1.88, "D"),
    "V5": ("reference", [5.0, 5.0, 5.0, 5.0, 5.0, 4.5, 4.5], 4.90, "A"),
    "V6": ("orchestrator", [5.0, 4.5, 4.0, 4.5, 5.0, 3.5, 4.5], 4.43, "B"),
    "V7": ("workflow", [4.5, 3.0, 4.0, 3.0, 3.5, 2.5, 3.5], 3.55, "B"),
}

# Full per-check reconstructions whose compute() output must equal canonical (caps included).
VIGNETTE_CHECKS = {
    "V2": ("tool-wrapper", {
        "spec_compliance": ["PASS"] * 7 + ["FAIL"],
        "trigger_precision": ["PASS", "FAIL", "PASS", "PASS"],
        "workflow_quality": ["PASS", "PASS", "PASS", "PASS", "FAIL", "PARTIAL"],
        "token_efficiency": ["PASS", "PASS", "PASS", "PASS", "PARTIAL"],
        "safety": ["PASS", "PASS", "PASS", "PARTIAL", "FAIL", "N-A"],
        "robustness_evaluability": ["PASS", "FAIL", "FAIL", "PARTIAL", "PASS"],
        "portability": ["PARTIAL", "N-A", "PASS", "PASS"]}, 3.95, "B"),
    "V5": ("reference", {
        "spec_compliance": ["PASS"] * 8,
        "trigger_precision": ["PASS", "PASS", "PASS", "N-A"],
        "workflow_quality": ["PASS", "PASS", "N-A", "N-A", "N-A", "N-A"],
        "token_efficiency": ["PASS"] * 5,
        "safety": ["PASS", "PASS", "PASS", "PASS", "N-A", "N-A"],
        "robustness_evaluability": ["PASS", "PARTIAL", "PASS", "N-A", "PASS"],
        "portability": ["PARTIAL", "N-A", "PASS", "PASS"]}, 4.90, "A"),
    "V7": ("workflow", {  # adversarial: trigger c1 critical FAIL, robustness c2 critical FAIL
        "spec_compliance": ["PASS"] * 7 + ["FAIL"],
        "trigger_precision": ["FAIL", "PASS", "PASS", "N-A"],
        "workflow_quality": ["PASS", "FAIL", "PARTIAL", "PASS", "PASS", "PASS"],
        "token_efficiency": ["PARTIAL", "PASS", "PASS", "FAIL", "FAIL"],
        "safety": ["PASS", "PARTIAL", "FAIL", "PASS", "N-A", "N-A"],
        "robustness_evaluability": ["PASS", "FAIL", "FAIL", "N-A", "PARTIAL"],
        "portability": ["PARTIAL", "N-A", "PASS", "PARTIAL"]}, 3.55, "B"),
}


class TestBandingAndArithmetic(unittest.TestCase):
    def test_grade_bands(self):
        self.assertEqual(score.band(4.50), "A")
        self.assertEqual(score.band(4.49), "B")
        self.assertEqual(score.band(3.50), "B")
        self.assertEqual(score.band(1.49), "F")

    def test_half_even_rounding(self):
        self.assertEqual(score.half_step(4.25), 4.0)   # midpoint -> even
        self.assertEqual(score.half_step(4.75), 5.0)   # midpoint -> even (5.0)
        self.assertEqual(score.half_step(4.30), 4.5)

    def test_vignette_weighted_arithmetic(self):
        for name, (arch, scores, ws, grade) in VIGNETTE_SCORES.items():
            got = score.two_dec(sum(w * s for w, s in zip(score.WEIGHTS[arch], scores)) / 100)
            self.assertEqual(got, ws, f"{name} weighted")
            self.assertEqual(score.band(got), grade, f"{name} grade")


class TestVignetteFullCompute(unittest.TestCase):
    def test_full_reproduction_with_caps(self):
        for name, (arch, checks, ws, grade) in VIGNETTE_CHECKS.items():
            comp = compute(arch, checks)
            self.assertEqual(comp["weighted_score"], ws, f"{name} weighted")
            self.assertEqual(comp["grade"], grade, f"{name} grade")
        # V7's critical FAILs must produce auto-caps of 3.0 on both dimensions.
        comp = compute("workflow", VIGNETTE_CHECKS["V7"][1])
        self.assertEqual(comp["dimensions"]["trigger_precision"]["cap"], 3.0)
        self.assertEqual(comp["dimensions"]["robustness_evaluability"]["cap"], 3.0)
        self.assertEqual(comp["detail"]["trigger_precision"]["final"], 3.0)


class TestCriticalCaps(unittest.TestCase):
    def test_each_critical_index_caps_at_3(self):
        cases = {
            "trigger_precision": ["FAIL", "PASS", "PASS", "PASS"],
            "safety": ["PASS", "PASS", "PASS", "FAIL", "PASS", "PASS"],
            "robustness_evaluability": ["PASS", "FAIL", "PASS", "PASS", "PASS"],
        }
        for dim, checks in cases.items():
            cb = allpass()
            cb[dim] = checks
            comp = compute("workflow", cb)
            self.assertEqual(comp["detail"][dim]["final"], 3.0, f"{dim} not capped")
            self.assertEqual(comp["dimensions"][dim]["cap"], 3.0, f"{dim} cap not recorded")

    def test_partial_on_critical_does_not_cap(self):
        cb = allpass()
        cb["trigger_precision"] = ["PARTIAL", "PASS", "PASS", "PASS"]
        comp = compute("workflow", cb)
        self.assertIsNone(comp["dimensions"]["trigger_precision"]["cap"])

    def test_validate_rejects_critical_fail_without_cap(self):
        # Hand-author a verdict with trigger c1 FAIL but cap omitted (the old bypass).
        comp = compute("workflow", allpass())  # start from a valid all-PASS verdict
        comp["dimensions"]["trigger_precision"] = {
            "score": 4.0, "checks": ["FAIL", "PASS", "PASS", "PASS"],
            "adjustment": 0, "adjustment_note": None, "cap": None}
        v = verdict_from(comp, meets=False)
        # recompute weighted_score by hand for this tampered verdict is unnecessary; validate
        # should reject the missing cap regardless of the score mismatch.
        rc, out, err = run("validate", v)
        self.assertEqual(rc, 1)
        self.assertIn("critical", err.lower())

    def test_validate_accepts_critical_fail_with_cap(self):
        cb = allpass()
        cb["trigger_precision"] = ["FAIL", "PASS", "PASS", "PASS"]
        comp = compute("workflow", cb)  # compute now sets cap 3.0, score 3.0
        v = verdict_from(comp, meets=False)
        rc, out, err = run("validate", v)
        self.assertEqual(rc, 0, err)

    def test_no_usable_trigger_cannot_meet_bar(self):
        # trigger c1 FAIL -> dim 3.0 < floor 3.5 -> meets_bar must be false even if weighted >= 4.5
        cb = allpass()
        cb["trigger_precision"] = ["FAIL", "PASS", "PASS", "PASS"]
        comp = compute("workflow", cb)
        self.assertLess(comp["detail"]["trigger_precision"]["final"], score.DIMENSION_FLOOR)
        v = verdict_from(comp, meets=True)
        rc, out, err = run("validate", v)
        self.assertEqual(rc, 1, "a skill with no usable trigger must not validate as meets_bar")


class TestBandStability(unittest.TestCase):
    def test_allpass_is_stable(self):
        comp = compute("workflow", allpass())
        self.assertTrue(comp["band_stability"]["band_stable"])
        self.assertFalse(comp["band_stability"]["gate_fragile"])

    def test_455_is_gate_fragile(self):
        cb = {"spec_compliance": ["PASS"] * 5 + ["FAIL"] * 3,
              "trigger_precision": ["PASS", "PASS", "PASS", "FAIL"],
              "workflow_quality": ["PASS"] * 6, "token_efficiency": ["PASS"] * 5,
              "safety": ["PASS"] * 6, "robustness_evaluability": ["PASS"] * 5,
              "portability": ["PASS"] * 4}
        comp = compute("workflow", cb)
        self.assertEqual(comp["weighted_score"], 4.55)
        self.assertTrue(comp["band_stability"]["gate_fragile"])

    def test_gate_fragile_requires_ensemble(self):
        cb = {"spec_compliance": ["PASS"] * 5 + ["FAIL"] * 3,
              "trigger_precision": ["PASS", "PASS", "PASS", "FAIL"],
              "workflow_quality": ["PASS"] * 6, "token_efficiency": ["PASS"] * 5,
              "safety": ["PASS"] * 6, "robustness_evaluability": ["PASS"] * 5,
              "portability": ["PASS"] * 4}
        comp = compute("workflow", cb)  # weighted 4.55, gate-fragile
        rc_single, _, err = run("validate", verdict_from(comp, mode="single", meets=True))
        self.assertEqual(rc_single, 1, "gate-fragile single-mode meets_bar must be rejected")
        self.assertIn("ensemble", err.lower())
        rc_ens, _, err2 = run("validate", verdict_from(comp, mode="ensemble", meets=True))
        self.assertEqual(rc_ens, 0, err2)


class TestGateRules(unittest.TestCase):
    def test_allpass_meets_bar(self):
        v = verdict_from(compute("workflow", allpass()), meets=True)
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 0, err)

    def test_floor_blocks_meets_bar(self):
        cb = allpass()
        cb["robustness_evaluability"] = ["PASS", "PASS", "FAIL", "FAIL", "N-A"]  # base 3.0
        comp = compute("workflow", cb)
        self.assertEqual(comp["detail"]["robustness_evaluability"]["final"], 3.0)
        rc, _, err = run("validate", verdict_from(comp, meets=True))
        self.assertEqual(rc, 1)
        self.assertIn("floor", err.lower())

    def test_domain_claim_skill_needs_correctness_tasks(self):
        # All-pass domain-claim skill with a single correctness task cannot meet the bar.
        v = verdict_from(compute("workflow", allpass()), meets=True,
                         domain_claims=True, correctness_tasks=1)
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1)
        self.assertIn("correctness_tasks", err.lower())

    def test_domain_claim_correctness_met_meets_bar(self):
        # Helper default: probe_model "probe-m" != reviewer_model "m" -> model-independent.
        v = verdict_from(compute("workflow", allpass()), meets=True,
                         domain_claims=True, correctness_tasks=3)
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 0, err)

    def test_same_model_probe_blocks_bar(self):
        # >=3 correctness tasks but the probe ran on the scorer's own model with no reason:
        # independence unestablished -> the bar must stay blocked.
        v = verdict_from(compute("workflow", allpass()), meets=True,
                         domain_claims=True, correctness_tasks=3,
                         probe_model="m", reviewer_model="m", same_model_probe_reason=None)
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1)
        self.assertIn("probe model", err.lower())

    def test_distinct_probe_model_meets_bar(self):
        v = verdict_from(compute("workflow", allpass()), meets=True,
                         domain_claims=True, correctness_tasks=3,
                         probe_model="other-model", reviewer_model="m")
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 0, err)

    def test_same_model_reason_allows_bar(self):
        # Genuine single-model environment: same model, but an explicit reason is recorded.
        v = verdict_from(compute("workflow", allpass()), meets=True,
                         domain_claims=True, correctness_tasks=3,
                         probe_model="m", reviewer_model="m",
                         same_model_probe_reason="only one model available in this environment")
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 0, err)

    def test_domain_claim_omitting_probe_model_blocks_bar(self):
        # Neither a probe_model nor a reason recorded -> independence unestablished (conservative).
        v = verdict_from(compute("workflow", allpass()), meets=True,
                         domain_claims=True, correctness_tasks=3)
        v.pop("probe_model", None)
        v.pop("same_model_probe_reason", None)
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1)
        self.assertIn("probe model", err.lower())

    def test_probe_model_requires_probe_run(self):
        # A recorded probe model with no probe is contradictory, independent of the gate.
        v = verdict_from(compute("workflow", allpass()), meets=False,
                         probe_run=False, probe_model="some-model",
                         domain_claims=False, correctness_tasks=0,
                         probe_skip_reason="no executable workflow")
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1)
        self.assertIn("probe_model", err.lower())

    def test_non_domain_skill_may_skip_correctness(self):
        # A skill with no domain claims can meet the bar without correctness tasks.
        v = verdict_from(compute("workflow", allpass()), meets=True,
                         domain_claims=False, correctness_tasks=0,
                         probe_run=False, probe_skip_reason="pure reference; no executable workflow")
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 0, err)

    def test_correctness_fields_default_conservatively(self):
        # Omitting both fields defaults to domain_claims true / 0 tasks, which blocks the bar.
        v = verdict_from(compute("workflow", allpass()), meets=True)
        del v["domain_claims"]
        del v["correctness_tasks"]
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1, "omitting correctness fields must not let a domain skill meet the bar")

    def test_correctness_tasks_require_probe_run(self):
        v = verdict_from(compute("workflow", allpass()), meets=False,
                         domain_claims=True, correctness_tasks=2, probe_run=False)
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1)
        self.assertIn("probe", err.lower())

    def test_net_adjustment_cap(self):
        dims = {k: {"checks": ["PASS"] * LEN[k]} for k in score.DIMENSIONS}
        dims["spec_compliance"].update(adjustment=-0.5, adjustment_note="x")
        dims["workflow_quality"].update(adjustment=-0.5, adjustment_note="x")
        rc, _, err = run("compute", {"archetype": "workflow", "dimensions": dims})
        self.assertEqual(rc, 2)
        self.assertIn("net weighted adjustment", err)


class TestDepthConstraints(unittest.TestCase):
    def test_triage_requires_nulls(self):
        v = verdict_from(compute("workflow", allpass()), depth="triage", meets=False)
        v["weighted_score"] = None
        v["grade"] = None
        for k in score.DIMENSIONS:
            v["dimensions"][k] = None
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 0, err)

    def test_triage_nonnull_scores_rejected(self):
        v = verdict_from(compute("workflow", allpass()), depth="triage", meets=False)
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1)

    def test_incremental_never_meets_bar(self):
        v = verdict_from(compute("workflow", allpass()), depth="incremental", meets=True,
                         base_verdict_commit="deadbee")
        rc, _, err = run("validate", v)
        self.assertEqual(rc, 1)


class TestShippedExample(unittest.TestCase):
    def _example_verdict(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            text = fh.read()
        block = text.rsplit("```json", 1)[1].split("```", 1)[0]
        return json.loads(block)

    def test_example_validates(self):
        v = self._example_verdict()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(v, f)
            path = f.name
        try:
            r = subprocess.run([sys.executable, SCORE, "validate", path],
                               capture_output=True, text=True)
        finally:
            os.unlink(path)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_example_recomputes(self):
        v = self._example_verdict()
        cb = {k: v["dimensions"][k]["checks"] for k in score.DIMENSIONS}
        extra = {k: {"adjustment": v["dimensions"][k]["adjustment"],
                     "adjustment_note": v["dimensions"][k]["adjustment_note"]}
                 for k in score.DIMENSIONS if v["dimensions"][k]["adjustment"]}
        comp = compute(v["archetype"], cb, extra)
        self.assertEqual(comp["weighted_score"], v["weighted_score"])
        self.assertEqual(comp["grade"], v["grade"])


class TestNAAllowlist(unittest.TestCase):
    def test_na_on_unlicensed_check_rejected(self):
        # spec_compliance has no rubric "N-A if" condition — N-A there is a denominator dodge.
        cb = allpass()
        cb["spec_compliance"] = ["N-A"] + ["PASS"] * 7
        rc, _, err = run_compute_raw("workflow", cb)
        self.assertEqual(rc, 2)
        self.assertIn("not licensed", err.lower())

    def test_na_on_licensed_check_ok(self):
        # safety c6 (index 5, embedded commands) is licensed N-A.
        cb = allpass()
        cb["safety"] = ["PASS"] * 5 + ["N-A"]
        comp = compute("workflow", cb)
        self.assertEqual(comp["dimensions"]["safety"]["score"], 5.0)

    def test_workflow_na_on_workflow_check_rejected(self):
        # A workflow skill cannot N-A "stop conditions" (index 4) to dodge a FAIL.
        cb = allpass()
        cb["workflow_quality"] = ["PASS", "PASS", "PASS", "PASS", "N-A", "PASS"]
        rc, _, err = run_compute_raw("workflow", cb)
        self.assertEqual(rc, 2)
        self.assertIn("not licensed", err.lower())

    def test_reference_relaxes_workflow_na(self):
        # The same N-A is legitimate for a reference/knowledge skill with minimal workflow.
        cb = allpass()
        cb["workflow_quality"] = ["PASS", "PASS", "N-A", "N-A", "N-A", "N-A"]
        comp = compute("reference", cb)
        self.assertEqual(comp["dimensions"]["workflow_quality"]["score"], 5.0)

    def test_user_invoked_arg_hint_na(self):
        # Re-scoped Dim2 c2 (argument-hint, index 1) is N-A-able only for a user-invoked skill.
        cb = allpass()
        cb["trigger_precision"] = ["PASS", "N-A", "PASS", "PASS"]
        rc_disp, _, err = run_compute_raw("workflow", cb, invocation_model="dispatched")
        self.assertEqual(rc_disp, 2, "dispatched skill must not N-A the negative-trigger check")
        comp = compute("workflow", cb, invocation_model="user-invoked")
        self.assertEqual(comp["dimensions"]["trigger_precision"]["score"], 5.0)

    def test_validate_rejects_unlicensed_na(self):
        # The allowlist is enforced on the validate path too, not just compute.
        comp = compute("workflow", allpass())
        comp["dimensions"]["token_efficiency"] = {
            "score": 5.0, "checks": ["N-A", "PASS", "PASS", "PASS", "PASS"],
            "adjustment": 0, "adjustment_note": None, "cap": None}
        rc, _, err = run("validate", verdict_from(comp, meets=False))
        self.assertEqual(rc, 1)
        self.assertIn("not licensed", err.lower())


# Archetype-fragile fixture: strong everywhere except spec_compliance and token_efficiency at
# base 3.5 (both >= floor). tool-wrapper weights token lightly (10) so it clears the gate;
# reference weights token heavily (25) so it does not -> the A-grade hinges on the classification.
ARCH_FRAGILE = dict(allpass(),
                    spec_compliance=["PASS"] * 5 + ["FAIL"] * 3,            # base 3.5
                    token_efficiency=["PASS", "PASS", "PASS", "FAIL", "FAIL"])  # 3.4 -> 3.5


class TestArchetypeRobustness(unittest.TestCase):
    def test_fragile_detected(self):
        comp = compute("tool-wrapper", ARCH_FRAGILE)
        ar = comp["archetype_robustness"]
        self.assertGreaterEqual(comp["weighted_score"], 4.5)
        self.assertTrue(ar["archetype_fragile"])
        self.assertIn("reference", ar["profiles_below_gate"])

    def test_allpass_not_fragile(self):
        comp = compute("workflow", allpass())
        self.assertFalse(comp["archetype_robustness"]["archetype_fragile"])

    def test_fragile_meets_bar_requires_ensemble(self):
        comp = compute("tool-wrapper", ARCH_FRAGILE)
        rc_single, _, err = run("validate", verdict_from(
            comp, archetype="tool-wrapper", mode="single", meets=True))
        self.assertEqual(rc_single, 1, "archetype-fragile single-mode meets_bar must be rejected")
        self.assertIn("archetype", err.lower())
        rc_ens, _, err2 = run("validate", verdict_from(
            comp, archetype="tool-wrapper", mode="ensemble", meets=True))
        self.assertEqual(rc_ens, 0, err2)


class TestVerifyEvidence(unittest.TestCase):
    SKILL_MD = ("---\n"
                "name: demo-skill\n"
                "description: {desc}\n"
                "---\n\n# Demo\n\nBody line.\n")

    def _skill(self, name="demo-skill", desc="Does a demo thing; use when demoing."):
        import shutil
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        sk = os.path.join(root, name)
        os.makedirs(sk)
        with open(os.path.join(sk, "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write(self.SKILL_MD.format(desc=desc))
        return sk, desc

    def _run(self, verdict, skill_dir):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(verdict, f)
            path = f.name
        try:
            r = subprocess.run([sys.executable, SCORE, "verify-evidence", path, skill_dir],
                               capture_output=True, text=True)
        finally:
            os.unlink(path)
        return r.returncode, r.stdout, r.stderr

    @staticmethod
    def _verdict(desc_chars, spec_checks=None, findings=None):
        return {"dimensions": {"spec_compliance": {"checks": spec_checks or ["PASS"] * 8}},
                "metrics": {"description_chars": desc_chars}, "findings": findings or []}

    def test_clean_skill_grounds_ok(self):
        sk, desc = self._skill()
        rc, out, err = self._run(self._verdict(len(desc)), sk)
        self.assertEqual(rc, 0, err)
        self.assertIn("metadata fact", out)

    def test_name_dir_mismatch_flagged_against_pass(self):
        sk, desc = self._skill(name="actual-dir-name")  # frontmatter still says demo-skill
        rc, _, err = self._run(self._verdict(len(desc)), sk)
        self.assertEqual(rc, 1)
        self.assertIn("c2 marked pass", err.lower())

    def test_description_chars_mismatch_flagged(self):
        sk, desc = self._skill()
        rc, _, err = self._run(self._verdict(len(desc) + 99), sk)
        self.assertEqual(rc, 1)
        self.assertIn("description_chars", err.lower())

    def test_missing_skill_md_flagged(self):
        import shutil
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        rc, _, err = self._run(self._verdict(10), root)
        self.assertEqual(rc, 1)
        self.assertIn("skill.md not found", err.lower())

    def test_finding_grounding_still_enforced(self):
        sk, desc = self._skill()
        bad = [{"id": "P2-1", "file": "SKILL.md", "lines": "9999", "patch": ""}]
        rc, _, err = self._run(self._verdict(len(desc), findings=bad), sk)
        self.assertEqual(rc, 1)
        self.assertIn("out of range", err.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
