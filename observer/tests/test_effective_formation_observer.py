from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from observer.effective_formation_observer import ObservationError, observe

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "observer" / "fixtures" / "bounded_context.json"
SCRIPT = ROOT / "observer" / "effective_formation_observer.py"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class EffectiveFormationObserverTests(unittest.TestCase):
    def test_report_boundary_is_explicit_and_non_authoritative(self) -> None:
        report = observe(load_fixture())
        self.assertEqual(report["schema"], "recursive-field/effective-formation-report/v0.2")
        self.assertEqual(
            report["boundary"],
            {
                "mode": "allowlisted_sanitized_fixture",
                "read_only": True,
                "content_free_by_enumeration": True,
                "non_authoritative": True,
                "canonical": False,
                "mutation_performed": False,
                "runtime_observed": False,
            },
        )
        self.assertEqual(report["coordinates"]["project"]["meaning"], "mutable_selector_not_identity")
        self.assertIn("authority", report["claims_not_made"])
        self.assertIn("identity", report["claims_not_made"])

    def test_first_enabled_candidate_wins_and_later_candidate_is_shadowed(self) -> None:
        report = observe(load_fixture())
        prompt = next(
            item for item in report["selection"]
            if item["kind"] == "prompt" and item["name"] == "system.main"
        )
        self.assertEqual(prompt["selection_status"], "selected")
        self.assertEqual(prompt["winner"], "project:profile:system-main")
        self.assertEqual(
            [candidate["disposition"] for candidate in prompt["candidates"]],
            ["winner", "shadowed"],
        )
        self.assertEqual(prompt["relation"], "selection_not_authority")

    def test_disabled_only_candidate_is_unavailable(self) -> None:
        report = observe(load_fixture())
        mutation_probe = next(
            item for item in report["selection"]
            if item["kind"] == "local_tool" and item["name"] == "tool.access"
        )
        self.assertEqual(mutation_probe["selection_status"], "unavailable")
        self.assertIsNone(mutation_probe["winner"])
        self.assertEqual(mutation_probe["candidates"][0]["disposition"], "disabled")

    def test_equal_precedence_is_reported_as_ambiguous(self) -> None:
        fixture = load_fixture()
        fixture["resources"].append(
            {
                "kind": "prompt",
                "name": "system.main",
                "source_ref": "project:alternate:system-main",
                "precedence_tier": "project_profile",
                "enabled": True,
                "condition": "satisfied",
                "evidence": "sanitized_fixture",
            }
        )
        report = observe(fixture)
        prompt = next(
            item for item in report["selection"]
            if item["kind"] == "prompt" and item["name"] == "system.main"
        )
        self.assertEqual(prompt["selection_status"], "ambiguous")
        self.assertIsNone(prompt["winner"])
        self.assertEqual(
            sum(candidate["disposition"] == "ambiguous_winner" for candidate in prompt["candidates"]),
            2,
        )

    def test_policy_reports_enforcement_without_inventing_authority(self) -> None:
        report = observe(load_fixture())
        policies = {item["capability"]: item for item in report["enforcement"]}
        blocked = policies["local:mutation-probe"]
        self.assertEqual(blocked["decision"], "block")
        self.assertTrue(blocked["structurally_enforced_at_reported_boundary"])
        self.assertEqual(blocked["authority"], "not_established")
        self.assertEqual(blocked["consequence_evidence"], "not_observed")
        invariant = policies["local:response"]
        self.assertFalse(invariant["structurally_enforced_at_reported_boundary"])

    def test_unknown_or_content_bearing_fields_are_rejected(self) -> None:
        fixture = load_fixture()
        fixture["resources"][0]["content"] = "private material"
        with self.assertRaises(ObservationError):
            observe(fixture)

        fixture = load_fixture()
        fixture["unknowns"][0]["statement"] = "Inspect https://private.invalid/state"
        with self.assertRaises(ObservationError):
            observe(fixture)

    def test_output_is_deterministic_for_unchanged_input(self) -> None:
        fixture = load_fixture()
        self.assertEqual(observe(copy.deepcopy(fixture)), observe(copy.deepcopy(fixture)))

    def test_cli_reads_fixture_and_leaves_it_unchanged(self) -> None:
        before = FIXTURE.read_bytes()
        before_stat = FIXTURE.stat()
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "bounded_context.json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        rendered = json.loads(completed.stdout)
        self.assertTrue(rendered["boundary"]["read_only"])
        self.assertEqual(FIXTURE.read_bytes(), before)
        self.assertEqual(FIXTURE.stat().st_mtime_ns, before_stat.st_mtime_ns)


if __name__ == "__main__":
    unittest.main()
