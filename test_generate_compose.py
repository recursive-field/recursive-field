#!/usr/bin/env python3
"""Contract tests for the Phase 3 Level 2 Compose generator."""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from dataclasses import replace
from pathlib import Path
from unittest import mock

import generate_compose as generator


GENESIS = "11111111-1111-4111-8111-111111111111"
AGENT_IDS = {
    "alpha": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "zeta": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
}
MESH_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
GATEWAY_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
SCHEMA_VERSION = "1.0.0"


def write_json(path: Path, value: dict, *, reverse_keys: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if reverse_keys:
        value = dict(reversed(list(value.items())))
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_field(
    root: Path,
    *,
    agent_order: tuple[str, ...] = ("zeta", "alpha"),
    reverse_keys: bool = False,
    with_env: bool = True,
    gateway_slug: str = "mesh-http",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    write_json(
        root / ".recursive-field-root",
        {"genesis_uuid": GENESIS, "schema_version": SCHEMA_VERSION},
        reverse_keys=reverse_keys,
    )
    for directory in ("agents", "mesh", "gateways", "tmp"):
        (root / directory).mkdir()
    write_json(root / "tmp" / "field_env.json", {"field_root": str(root)})
    if with_env:
        (root / ".env").write_text(
            f"LIBRARY=dotenv-library\nFIELD_ROOT={root}\nPORT_BASE=45000\n"
            "IMAGE_NAME=example/agent:dotenv\n",
            encoding="utf-8",
        )

    for slug in agent_order:
        agent_dir = root / "agents" / slug
        (agent_dir / "memory").mkdir(parents=True)
        (agent_dir / "observations").mkdir()
        write_json(
            agent_dir / "identity.json",
            {
                "agent_id": AGENT_IDS[slug],
                "slug": slug,
                "field_genesis_uuid": GENESIS,
                "role": f"{slug} role",
                "schema_version": SCHEMA_VERSION,
            },
            reverse_keys=reverse_keys,
        )

    mesh_dir = root / "mesh" / "alpha-zeta-mesh"
    mesh_dir.mkdir()
    write_json(
        mesh_dir / "channel.json",
        {
            "mesh_id": MESH_ID,
            "slug": "alpha-zeta-mesh",
            "field_genesis_uuid": GENESIS,
            "endpoints": [
                {"slug": "zeta", "agent_id": AGENT_IDS["zeta"]},
                {"slug": "alpha", "agent_id": AGENT_IDS["alpha"]},
            ],
            "channel_type": "peer-to-peer",
            "schema_version": SCHEMA_VERSION,
        },
        reverse_keys=reverse_keys,
    )
    (mesh_dir / "queue.jsonl").write_text("", encoding="utf-8")

    gateway_dir = root / "gateways" / gateway_slug
    gateway_dir.mkdir()
    write_json(
        gateway_dir / "manifest.json",
        {
            "gateway_id": GATEWAY_ID,
            "slug": gateway_slug,
            "field_genesis_uuid": GENESIS,
            "target_type": "mesh",
            "target_slug": "alpha-zeta-mesh",
            "target_id": MESH_ID,
            "gateway_type": "http",
            "status": "active",
            "schema_version": SCHEMA_VERSION,
        },
        reverse_keys=reverse_keys,
    )
    return root


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


class FieldCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = make_field(Path(self.temp.name) / "field")

    def plan(self, **kwargs) -> generator.GenerationPlan:
        kwargs.setdefault("start", self.root)
        kwargs.setdefault("environ", {})
        return generator.plan_generation(**kwargs)

    def generate(self, **kwargs) -> dict[str, object]:
        kwargs.setdefault("start", self.root)
        kwargs.setdefault("environ", {})
        return generator.generate_compose(**kwargs)

    def mutate_json(self, relative: str, mutation) -> None:
        path = self.root / relative
        data = read_json(path)
        mutation(data)
        write_json(path, data)


class ResolutionTests(FieldCase):
    def test_precedence_explicit_then_environment_then_dotenv_then_defaults(self) -> None:
        env_plan = self.plan(environ={"LIBRARY": "environment-library", "PORT_BASE": "46000"})
        self.assertEqual(env_plan.config.library, "environment-library")
        self.assertEqual(env_plan.config.port_base, 46000)

        explicit = self.plan(
            library="explicit-library",
            port_base="47000",
            environ={"LIBRARY": "environment-library", "PORT_BASE": "46000"},
        )
        self.assertEqual(explicit.config.library, "explicit-library")
        self.assertEqual(explicit.config.port_base, 47000)

        dotenv = self.plan(environ={"LIBRARY": "", "PORT_BASE": ""})
        self.assertEqual(dotenv.config.library, "dotenv-library")
        self.assertEqual(dotenv.config.port_base, 45000)

        (self.root / ".env").unlink()
        defaults = self.plan(environ={})
        self.assertEqual(defaults.config.library, generator.DEFAULT_LIBRARY)
        self.assertEqual(defaults.config.port_base, generator.DEFAULT_PORT_BASE)

    def test_field_root_all_sources_must_match_discovery(self) -> None:
        self.assertEqual(
            self.plan(field_root=self.root, environ={"FIELD_ROOT": str(self.root)}).config.field_root,
            self.root.resolve(),
        )
        for kwargs in (
            {"field_root": self.root.parent},
            {"environ": {"FIELD_ROOT": str(self.root.parent)}},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(generator.GenerationError):
                self.plan(**kwargs)
        (self.root / ".env").write_text(
            f"FIELD_ROOT={self.root.parent}\nLIBRARY=dotenv-library\nPORT_BASE=45000\n",
            encoding="utf-8",
        )
        with self.assertRaises(generator.GenerationError):
            self.plan()

    def test_env_is_never_rewritten(self) -> None:
        before = (self.root / ".env").read_bytes()
        self.generate(dry_run=True)
        self.assertEqual((self.root / ".env").read_bytes(), before)
        self.generate()
        self.assertEqual((self.root / ".env").read_bytes(), before)

    def test_compose_output_is_fixed_and_cannot_target_operator_files(self) -> None:
        env_before = (self.root / ".env").read_bytes()
        marker_before = (self.root / ".recursive-field-root").read_bytes()
        self.assertEqual(
            self.plan(out_path="docker-compose.yml").config.compose_path,
            self.root / "docker-compose.yml",
        )
        for target in (
            ".env",
            ".recursive-field-root",
            "README.md",
            "agents/alpha/identity.json",
            "gateways/mesh-http/nginx.conf",
        ):
            with self.subTest(target=target), self.assertRaisesRegex(
                generator.GenerationError, "fixed at FIELD_ROOT/docker-compose.yml"
            ):
                self.plan(out_path=target)
        self.assertEqual((self.root / ".env").read_bytes(), env_before)
        self.assertEqual((self.root / ".recursive-field-root").read_bytes(), marker_before)
        self.assertFalse(list(self.root.rglob(".*.tmp")))


class TopologyAndRenderingTests(FieldCase):
    def test_stable_order_and_port_formulas(self) -> None:
        plan = self.plan(port_base=44000)
        self.assertEqual([item.slug for item in plan.topology.agents], ["alpha", "zeta"])
        self.assertEqual([item.ssh_host_port for item in plan.topology.agents], [44022, 44122])
        active = [item for item in plan.topology.gateways if item.service_key]
        self.assertEqual([item.slug for item in active], ["mesh-http"])
        self.assertEqual(active[0].http_host_port, 44280)

    def test_agent_http_is_internal_port_80_only_and_no_event_port(self) -> None:
        text = self.plan(port_base=44000).compose_bytes.decode()
        self.assertIn('expose:\n      - "80"', text)
        self.assertIn('"44022:22"', text)
        self.assertIn('"44122:22"', text)
        self.assertIn('"44280:80"', text)
        self.assertNotIn('"44080:80"', text)
        self.assertNotIn("8000", text)
        self.assertNotIn("event", text.lower())

    def test_nginx_and_depends_on_have_exact_service_key_correspondence(self) -> None:
        plan = self.plan()
        gateway = next(item for item in plan.topology.gateways if item.service_key)
        nginx = dict(plan.nginx_bytes)[gateway.slug].decode()
        self.assertEqual(
            gateway.upstream_service_keys,
            ("agent-alpha", "agent-zeta"),
        )
        for service_key in gateway.upstream_service_keys:
            self.assertEqual(nginx.count(f"server {service_key}:80;"), 1)
        self.assertNotIn(gateway.container_name or "missing", nginx)
        compose = plan.compose_bytes.decode()
        depends_section = compose.split("depends_on:", 1)[1]
        self.assertIn('- "agent-alpha"', depends_section)
        self.assertIn('- "agent-zeta"', depends_section)

    def test_mount_permissions_and_docker_socket_exclusion(self) -> None:
        text = self.plan().compose_bytes.decode()
        host_root = self.root.resolve().as_posix()
        for slug in ("alpha", "zeta"):
            self.assertIn(
                f"{host_root}/agents/{slug}:/a0/agents/{slug}:ro",
                text,
            )
            self.assertIn(
                f"{host_root}/agents/{slug}/memory:/a0/memory:rw",
                text,
            )
            self.assertIn(
                f"{host_root}/agents/{slug}/observations:/a0/observations:rw",
                text,
            )
        self.assertIn(f"{host_root}:/agent_orchestration:ro", text)
        self.assertIn(
            f"{host_root}/mesh/alpha-zeta-mesh/queue.jsonl:"
            "/a0/mesh/alpha-zeta-mesh/queue.jsonl:rw",
            text,
        )
        self.assertNotIn("${FIELD_ROOT}", text)
        self.assertNotIn(":/a0/agents/alpha:rw", text)
        self.assertNotIn("docker.sock", text.lower())

    def test_every_generated_output_starts_with_exact_marker(self) -> None:
        plan = self.plan()
        expected = (generator.GENERATED_MARKER + "\n").encode()
        self.assertTrue(plan.compose_bytes.startswith(expected))
        self.assertTrue(all(content.startswith(expected) for _, content in plan.nginx_bytes))

    def test_deterministic_bytes_across_repeats_creation_and_json_order(self) -> None:
        first = self.plan()
        second = self.plan()
        self.assertEqual(first.compose_bytes, second.compose_bytes)
        self.assertEqual(first.nginx_bytes, second.nginx_bytes)

        other_temp = tempfile.TemporaryDirectory()
        self.addCleanup(other_temp.cleanup)
        other = make_field(
            Path(other_temp.name) / "field",
            agent_order=("alpha", "zeta"),
            reverse_keys=True,
        )
        other_plan = generator.plan_generation(start=other, environ={})
        # Absolute host roots are intentionally bound into Compose. Normalize
        # only that validated input when comparing shuffled creation/key order.
        first_normalized = first.compose_bytes.replace(str(self.root).encode(), b"<FIELD_ROOT>")
        other_normalized = other_plan.compose_bytes.replace(str(other).encode(), b"<FIELD_ROOT>")
        self.assertEqual(first_normalized, other_normalized)
        self.assertEqual(first.nginx_bytes, other_plan.nginx_bytes)

    def test_deterministic_across_pythonhashseed(self) -> None:
        script = (
            "import hashlib,generate_compose as g;"
            f"p=g.plan_generation(start={str(self.root)!r},environ={{}});"
            "print(hashlib.sha256(p.compose_bytes).hexdigest());"
            "print(hashlib.sha256(b''.join(x[1] for x in p.nginx_bytes)).hexdigest())"
        )
        hashes = []
        for seed in ("1", "987654"):
            env = os.environ.copy()
            env.update({"PYTHONHASHSEED": seed, "PYTHONDONTWRITEBYTECODE": "1"})
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=Path(__file__).parent,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            hashes.append(completed.stdout)
        self.assertEqual(hashes[0], hashes[1])


class PlanningAndApplyTests(FieldCase):
    def test_generation_completes_within_speed_budget(self) -> None:
        started = time.perf_counter()
        result = self.generate(dry_run=True)
        elapsed = time.perf_counter() - started

        self.assertIn("plan", result)
        self.assertLess(elapsed, 1.5, f"compose generation took {elapsed:.3f}s")

    def test_dry_run_returns_plan_and_bytes_without_mutation(self) -> None:
        before = snapshot_files(self.root)
        result = self.generate(dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIsInstance(result["compose_bytes"], bytes)
        self.assertEqual({item["action"] for item in result["actions"]}, {"create"})
        self.assertEqual(snapshot_files(self.root), before)
        self.assertFalse((self.root / "docker-compose.yml").exists())
        self.assertFalse((self.root / "gateways" / "mesh-http" / "nginx.conf").exists())

    def test_apply_writes_marked_outputs_and_is_idempotent(self) -> None:
        first = self.generate()
        compose = self.root / "docker-compose.yml"
        nginx = self.root / "gateways" / "mesh-http" / "nginx.conf"
        self.assertTrue(compose.read_text().startswith(generator.GENERATED_MARKER + "\n"))
        self.assertTrue(nginx.read_text().startswith(generator.GENERATED_MARKER + "\n"))
        before = (compose.read_bytes(), nginx.read_bytes())
        second = self.generate()
        self.assertEqual({item["action"] for item in second["actions"]}, {"unchanged"})
        self.assertEqual((compose.read_bytes(), nginx.read_bytes()), before)
        self.assertFalse(list(self.root.rglob(".*.tmp")))
        self.assertFalse(first["dry_run"])

    def test_unmarked_nginx_requires_explicit_adoption(self) -> None:
        nginx = self.root / "gateways" / "mesh-http" / "nginx.conf"
        nginx.write_text("# operator config\nevents {}\n", encoding="utf-8")
        with self.assertRaises(generator.GenerationError):
            self.generate()
        self.assertEqual(nginx.read_text(), "# operator config\nevents {}\n")
        self.generate(adopt_existing=True)
        self.assertTrue(nginx.read_text().startswith(generator.GENERATED_MARKER + "\n"))

    def test_validation_failure_preserves_existing_outputs(self) -> None:
        self.generate()
        compose = self.root / "docker-compose.yml"
        nginx = self.root / "gateways" / "mesh-http" / "nginx.conf"
        before = (compose.read_bytes(), nginx.read_bytes())
        self.mutate_json(
            "gateways/mesh-http/manifest.json",
            lambda value: value.__setitem__("target_slug", "missing-mesh"),
        )
        with self.assertRaises(generator.GenerationError):
            self.generate()
        self.assertEqual((compose.read_bytes(), nginx.read_bytes()), before)

    def test_apply_uses_atomic_replace_and_cleans_staging_files(self) -> None:
        plan = self.plan()
        real_replace = os.replace
        calls: list[tuple[object, object]] = []

        def recording_replace(source, destination, **kwargs):
            calls.append((source, destination, kwargs))
            return real_replace(source, destination, **kwargs)

        with mock.patch.object(generator.os, "replace", side_effect=recording_replace):
            generator.apply_plan(plan)
        self.assertEqual(len(calls), 2)
        self.assertTrue(
            all(
                kwargs.get("src_dir_fd") == kwargs.get("dst_dir_fd")
                and kwargs.get("src_dir_fd") is not None
                and "/" not in str(source)
                and "/" not in str(destination)
                for source, destination, kwargs in calls
            )
        )
        self.assertFalse(list(self.root.rglob(".*.tmp")))

    def test_duplicate_planned_output_path_fails_before_staging(self) -> None:
        base = self.plan()
        nginx_path = self.root / "gateways" / "mesh-http" / "nginx.conf"
        collided = replace(base.config, compose_path=nginx_path)
        before = snapshot_files(self.root)
        with mock.patch.object(generator, "_resolve_config", return_value=collided):
            with self.assertRaisesRegex(generator.GenerationError, "duplicate planned output path"):
                generator.plan_generation(start=self.root, environ={})
        self.assertEqual(snapshot_files(self.root), before)
        self.assertFalse(list(self.root.rglob(".*.tmp")))

    def test_replace_revalidates_file_identity_after_staging(self) -> None:
        self.generate()
        compose = self.root / "docker-compose.yml"
        original = compose.read_bytes()
        plan = self.plan(image_name="example/agent:changed")
        real_stage = generator._stage_output
        raced = False

        def race_after_stage(output, parent_fd):
            nonlocal raced
            staged = real_stage(output, parent_fd)
            if output.path == compose and not raced:
                raced = True
                replacement = compose.with_name(".race-replacement")
                replacement.write_bytes(original)
                os.replace(replacement, compose)
            return staged

        with mock.patch.object(generator, "_stage_output", side_effect=race_after_stage):
            with self.assertRaisesRegex(generator.GenerationError, "identity or content changed"):
                generator.apply_plan(plan)
        self.assertEqual(compose.read_bytes(), original)
        self.assertFalse(list(self.root.rglob(".*.tmp")))

    def test_stale_delete_revalidates_file_identity_immediately_before_unlink(self) -> None:
        self.generate()
        nginx = self.root / "gateways" / "mesh-http" / "nginx.conf"
        original = nginx.read_bytes()
        self.mutate_json(
            "gateways/mesh-http/manifest.json",
            lambda value: value.__setitem__("status", "inactive"),
        )
        plan = self.plan()
        real_preflight = generator._preflight_output_at
        calls = 0

        def race_after_first_preflight(output, parent_fd):
            nonlocal calls
            real_preflight(output, parent_fd)
            if output.action == "delete" and calls == 0:
                calls += 1
                replacement = nginx.with_name(".race-replacement")
                replacement.write_bytes(original)
                os.replace(replacement, nginx)

        with mock.patch.object(generator, "_preflight_output_at", side_effect=race_after_first_preflight):
            with self.assertRaisesRegex(generator.GenerationError, "identity or content changed"):
                generator.apply_plan(plan)
        self.assertTrue(nginx.exists())
        self.assertEqual(nginx.read_bytes(), original)
        self.assertFalse(list(self.root.rglob(".*.tmp")))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_parent_swap_during_replace_fails_closed_outside_root(self) -> None:
        self.generate()
        gateway_dir = self.root / "gateways" / "mesh-http"
        nginx = gateway_dir / "nginx.conf"
        old_bytes = generator.GENERATED_MARKER.encode() + b"\n# prior generated bytes\n"
        nginx.write_bytes(old_bytes)
        plan = self.plan()
        self.assertEqual(next(item.action for item in plan.outputs if item.path == nginx), "replace")

        outside = self.root.parent / "outside-replace"
        outside.mkdir()
        outside_victim = outside / "nginx.conf"
        outside_bytes = b"outside victim must survive\n"
        outside_victim.write_bytes(outside_bytes)
        displaced = self.root / "gateways" / "mesh-http-displaced"
        real_stage = generator._stage_output
        swapped = False

        def swap_parent_after_stage(output, parent_fd):
            nonlocal swapped
            staged_name = real_stage(output, parent_fd)
            if output.path == nginx and not swapped:
                swapped = True
                gateway_dir.rename(displaced)
                gateway_dir.symlink_to(outside, target_is_directory=True)
            return staged_name

        with mock.patch.object(generator, "_stage_output", side_effect=swap_parent_after_stage):
            with self.assertRaisesRegex(
                generator.GenerationError, "safely traverse parent|parent was replaced"
            ):
                generator.apply_plan(plan)

        self.assertEqual(outside_victim.read_bytes(), outside_bytes)
        self.assertEqual((displaced / "nginx.conf").read_bytes(), old_bytes)
        self.assertFalse(list(displaced.glob(".*.tmp")))
        self.assertFalse(list(outside.glob(".*.tmp")))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_parent_swap_during_stale_delete_fails_closed_outside_root(self) -> None:
        self.generate()
        gateway_dir = self.root / "gateways" / "mesh-http"
        nginx = gateway_dir / "nginx.conf"
        old_bytes = nginx.read_bytes()
        self.mutate_json(
            "gateways/mesh-http/manifest.json",
            lambda value: value.__setitem__("status", "inactive"),
        )
        plan = self.plan()
        self.assertEqual(next(item.action for item in plan.outputs if item.path == nginx), "delete")

        outside = self.root.parent / "outside-delete"
        outside.mkdir()
        outside_victim = outside / "nginx.conf"
        outside_bytes = b"outside victim must survive\n"
        outside_victim.write_bytes(outside_bytes)
        displaced = self.root / "gateways" / "mesh-http-displaced"
        real_preflight = generator._preflight_output_at
        swapped = False

        def swap_parent_after_preflight(output, parent_fd):
            nonlocal swapped
            real_preflight(output, parent_fd)
            if output.action == "delete" and not swapped:
                swapped = True
                gateway_dir.rename(displaced)
                gateway_dir.symlink_to(outside, target_is_directory=True)

        with mock.patch.object(
            generator, "_preflight_output_at", side_effect=swap_parent_after_preflight
        ):
            with self.assertRaisesRegex(
                generator.GenerationError, "safely traverse parent|parent was replaced"
            ):
                generator.apply_plan(plan)

        self.assertEqual(outside_victim.read_bytes(), outside_bytes)
        self.assertEqual((displaced / "nginx.conf").read_bytes(), old_bytes)
        self.assertFalse(list(displaced.glob(".*.tmp")))
        self.assertFalse(list(outside.glob(".*.tmp")))

    def test_stale_marked_nginx_removed_but_unowned_stale_preserved(self) -> None:
        self.generate()
        nginx = self.root / "gateways" / "mesh-http" / "nginx.conf"
        self.mutate_json(
            "gateways/mesh-http/manifest.json",
            lambda value: value.__setitem__("status", "inactive"),
        )
        plan = self.plan()
        stale = [item for item in plan.outputs if item.action == "delete"]
        self.assertEqual([item.path for item in stale], [nginx])
        generator.apply_plan(plan)
        self.assertFalse(nginx.exists())

        nginx.write_text("# operator-owned stale config\n", encoding="utf-8")
        plan = self.plan()
        self.assertFalse(any(item.path == nginx for item in plan.outputs))
        generator.apply_plan(plan)
        self.assertEqual(nginx.read_text(), "# operator-owned stale config\n")


class NegativeValidationTests(FieldCase):
    def test_unsupported_topology_schema_version_is_rejected(self) -> None:
        paths = [self.root / ".recursive-field-root"]
        paths.extend(self.root.glob("agents/*/identity.json"))
        paths.extend(self.root.glob("mesh/*/channel.json"))
        paths.extend(self.root.glob("gateways/*/manifest.json"))
        for path in paths:
            value = read_json(path)
            value["schema_version"] = "999.0"
            write_json(path, value)
        with self.assertRaisesRegex(generator.GenerationError, "unsupported topology schema_version"):
            self.plan()

    def test_malformed_namespace_and_slugs(self) -> None:
        for library in ("Upper", "has_underscore", "-leading", "trailing-", "a/b", ".."):
            with self.subTest(library=library), self.assertRaises(generator.GenerationError):
                self.plan(library=library)
        for slug in ("../escape", "/absolute", "bad/name", "Bad"):
            with self.subTest(slug=slug):
                original = read_json(self.root / "agents" / "alpha" / "identity.json")
                changed = dict(original, slug=slug)
                write_json(self.root / "agents" / "alpha" / "identity.json", changed)
                with self.assertRaises(generator.GenerationError):
                    self.plan()
                write_json(self.root / "agents" / "alpha" / "identity.json", original)

    def test_manifest_directory_mismatch_and_duplicate_ids(self) -> None:
        self.mutate_json(
            "agents/alpha/identity.json",
            lambda value: value.__setitem__("slug", "other"),
        )
        with self.assertRaises(generator.GenerationError):
            self.plan()
        self.mutate_json(
            "agents/alpha/identity.json",
            lambda value: value.__setitem__("slug", "alpha"),
        )
        self.mutate_json(
            "agents/zeta/identity.json",
            lambda value: value.__setitem__("agent_id", AGENT_IDS["alpha"]),
        )
        with self.assertRaises(generator.GenerationError):
            self.plan()

    def test_duplicate_service_keys_and_container_names_rejected(self) -> None:
        with self.assertRaisesRegex(generator.GenerationError, "service key"):
            generator._validate_unique_runtime_name(
                "agent-alpha", "lib-other", {"agent-alpha"}, set(), "duplicate"
            )
        with self.assertRaisesRegex(generator.GenerationError, "container name"):
            generator._validate_unique_runtime_name(
                "agent-other", "lib-alpha", set(), {"lib-alpha"}, "duplicate"
            )

        # Cross-kind duplicate slugs fail even earlier at topology normalization.
        self.mutate_json(
            "gateways/mesh-http/manifest.json",
            lambda value: value.update(
                {
                    "slug": "alpha",
                    "target_type": "agent",
                    "target_slug": "alpha",
                    "target_id": AGENT_IDS["alpha"],
                }
            ),
        )
        (self.root / "gateways" / "mesh-http").rename(self.root / "gateways" / "alpha")
        with self.assertRaisesRegex(generator.GenerationError, "topology slug"):
            self.plan(library="dotenv-library")

    def test_unknown_duplicate_or_mismatched_mesh_endpoints(self) -> None:
        path = self.root / "mesh" / "alpha-zeta-mesh" / "channel.json"
        original = read_json(path)
        variants = []
        unknown = json.loads(json.dumps(original))
        unknown["endpoints"][0]["slug"] = "unknown"
        variants.append(unknown)
        mismatch = json.loads(json.dumps(original))
        mismatch["endpoints"][0]["agent_id"] = AGENT_IDS["alpha"]
        variants.append(mismatch)
        duplicate = json.loads(json.dumps(original))
        duplicate["endpoints"][1] = dict(duplicate["endpoints"][0])
        variants.append(duplicate)
        empty = dict(original, endpoints=[])
        variants.append(empty)
        for value in variants:
            with self.subTest(value=value), self.assertRaises(generator.GenerationError):
                write_json(path, value)
                self.plan()
        write_json(path, original)

    def test_unknown_gateway_target_id_status_and_type(self) -> None:
        path = self.root / "gateways" / "mesh-http" / "manifest.json"
        original = read_json(path)
        variants = [
            dict(original, target_slug="missing"),
            dict(original, target_id=str(uuid.uuid4())),
            dict(original, status="mystery"),
            dict(original, gateway_type="socket"),
            dict(original, target_type="world"),
        ]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(generator.GenerationError):
                write_json(path, value)
                self.plan()
        write_json(path, original)

    def test_invalid_out_of_range_overflow_and_collision_ports(self) -> None:
        for value in ("abc", "44.5", -1, 0, 65536, True):
            with self.subTest(value=value), self.assertRaises(generator.GenerationError):
                self.plan(port_base=value)
        with self.assertRaises(generator.GenerationError):
            self.plan(port_base=65400)
        with self.assertRaisesRegex(generator.GenerationError, "collision"):
            generator._derived_port(44022, "second", {44022: "first"})

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_identity_queue_and_output_are_rejected(self) -> None:
        identity = self.root / "agents" / "alpha" / "identity.json"
        identity_copy = self.root / "identity-copy.json"
        identity_copy.write_bytes(identity.read_bytes())
        identity.unlink()
        identity.symlink_to(identity_copy)
        with self.assertRaises(generator.GenerationError):
            self.plan()
        identity.unlink()
        identity.write_bytes(identity_copy.read_bytes())

        queue = self.root / "mesh" / "alpha-zeta-mesh" / "queue.jsonl"
        queue_copy = self.root / "queue-copy.jsonl"
        queue_copy.write_text("", encoding="utf-8")
        queue.unlink()
        queue.symlink_to(queue_copy)
        with self.assertRaises(generator.GenerationError):
            self.plan()
        queue.unlink()
        queue.write_text("", encoding="utf-8")

        target = self.root / "compose-target.yml"
        target.write_text("target", encoding="utf-8")
        (self.root / "docker-compose.yml").symlink_to(target)
        with self.assertRaises(generator.GenerationError):
            self.plan()

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_output_escape_and_symlinked_ancestor_are_rejected(self) -> None:
        with self.assertRaises(generator.GenerationError):
            self.plan(out_path=self.root.parent / "outside.yml")
        real = self.root / "real-output"
        real.mkdir()
        (self.root / "linked-output").symlink_to(real, target_is_directory=True)
        with self.assertRaises(generator.GenerationError):
            self.plan(out_path="linked-output/docker-compose.yml")

    def test_docker_socket_appearance_is_rejected(self) -> None:
        with self.assertRaisesRegex(generator.GenerationError, "Docker socket"):
            self.plan(image_name="unix:///var/run/docker.sock")

    def test_noncanonical_ids_and_absolute_separator_coordinates_rejected(self) -> None:
        path = self.root / "agents" / "alpha" / "identity.json"
        original = read_json(path)
        changed = dict(original, agent_id=original["agent_id"].upper())
        write_json(path, changed)
        with self.assertRaises(generator.GenerationError):
            self.plan()
        write_json(path, original)

        gateway = self.root / "gateways" / "mesh-http" / "manifest.json"
        manifest = read_json(gateway)
        for target_slug in ("/absolute", "../traversal", "a/b", "a\\b"):
            with self.subTest(target_slug=target_slug), self.assertRaises(generator.GenerationError):
                write_json(gateway, dict(manifest, target_slug=target_slug))
                self.plan()


if __name__ == "__main__":
    unittest.main()
