#!/usr/bin/env python3
"""Focused contracts for the rendered systemd queue worker units."""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

import consume_queue as queue_worker


ROOT = Path(__file__).resolve().parent
SYSTEMD_DIR = ROOT / "systemd"
TEMPLATE_NAMES = (
    "queue-worker.service.in",
    "queue-worker.timer.in",
    "docker.service.d/field-root.conf.in",
)
PLACEHOLDERS = {
    "@FIELD_ROOT@": "/srv/field-root",
    "@AGENT_SLUG@": "observer",
    "@MESH_SLUG@": "observation-mesh",
    "@SERVICE_UNIT@": "queue-worker-observer-observation-mesh.service",
    "@LOCK_RUNTIME_DIR@": "queue-worker-observer-observation-mesh",
    "@LOCK_FILE@": "consume.lock",
}


def _render(template_name: str) -> str:
    rendered = (SYSTEMD_DIR / template_name).read_text(encoding="utf-8")
    for placeholder, value in PLACEHOLDERS.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


class SystemdTemplateTest(unittest.TestCase):
    def test_service_rendering_and_sandbox_contract(self) -> None:
        service = _render("queue-worker.service.in")
        self.assertIsNone(re.search(r"@[A-Z_]+@", service))

        required_lines = {
            "RequiresMountsFor=/srv/field-root",
            "Type=oneshot",
            "User=root",
            "Group=root",
            'Environment="FIELD_ROOT=/srv/field-root"',
            "RuntimeDirectory=queue-worker-observer-observation-mesh",
            "ExecCondition=/usr/bin/mountpoint --quiet -- /srv/field-root",
            (
                "ExecStart=/usr/bin/flock --nonblock --exclusive "
                "--conflict-exit-code=75 "
                "/run/queue-worker-observer-observation-mesh/consume.lock "
                "/usr/bin/python3 /srv/field-root/consume_queue.py observer "
                "observation-mesh --once"
            ),
            "SuccessExitStatus=4 75",
            "TimeoutStartSec=4min",
            "StandardOutput=journal",
            "StandardError=journal",
            "NoNewPrivileges=yes",
            "PrivateTmp=yes",
            "PrivateDevices=yes",
            "PrivateNetwork=yes",
            "ProtectSystem=strict",
            "ProtectHome=yes",
            "CapabilityBoundingSet=",
            "AmbientCapabilities=",
            "RestrictAddressFamilies=AF_UNIX",
            "IPAddressDeny=any",
            (
                "ReadWritePaths=/srv/field-root "
                "/run/queue-worker-observer-observation-mesh"
            ),
        }
        self.assertTrue(required_lines.issubset(set(service.splitlines())))
        self.assertNotIn("--once ", service)

    def test_timer_rendering_contract(self) -> None:
        timer = _render("queue-worker.timer.in")
        self.assertIsNone(re.search(r"@[A-Z_]+@", timer))
        required_lines = {
            "Unit=queue-worker-observer-observation-mesh.service",
            "OnBootSec=5s",
            "OnUnitActiveSec=5s",
            "Persistent=true",
        }
        self.assertTrue(required_lines.issubset(set(timer.splitlines())))

    def test_docker_drop_in_requires_exact_field_mount(self) -> None:
        drop_in = _render("docker.service.d/field-root.conf.in")
        self.assertEqual(
            drop_in,
            "[Unit]\nRequiresMountsFor=/srv/field-root\n",
        )

    def test_templates_expose_only_documented_placeholders(self) -> None:
        templates = "\n".join(
            (SYSTEMD_DIR / name).read_text(encoding="utf-8")
            for name in TEMPLATE_NAMES
        )
        self.assertEqual(set(re.findall(r"@[A-Z_]+@", templates)), set(PLACEHOLDERS))
        docker_template = (
            SYSTEMD_DIR / "docker.service.d/field-root.conf.in"
        ).read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"@[A-Z_]+@", docker_template)), {"@FIELD_ROOT@"})


class QueueWorkerDiscoveryTest(unittest.TestCase):
    def test_cli_uses_field_root_environment_as_discovery_start(self) -> None:
        result = {"status": "idle"}
        with (
            patch.dict(os.environ, {"FIELD_ROOT": "/srv/field-root"}),
            patch.object(queue_worker, "consume_queue", return_value=result) as consume,
        ):
            exit_code = queue_worker.main(["observer", "observation-mesh", "--once"])

        self.assertEqual(exit_code, 0)
        consume.assert_called_once_with(
            "observer",
            "observation-mesh",
            once=True,
            start="/srv/field-root",
        )

    def test_empty_field_root_environment_preserves_cwd_discovery(self) -> None:
        result = {"status": "idle"}
        with (
            patch.dict(os.environ, {"FIELD_ROOT": ""}),
            patch.object(queue_worker, "consume_queue", return_value=result) as consume,
        ):
            exit_code = queue_worker.main(["observer", "observation-mesh", "--once"])

        self.assertEqual(exit_code, 0)
        consume.assert_called_once_with(
            "observer", "observation-mesh", once=True, start=None
        )

    def test_explicit_function_start_is_unchanged(self) -> None:
        with (
            patch.object(queue_worker, "find_root", return_value=None) as find_root,
            self.assertRaisesRegex(RuntimeError, "Could not locate field root"),
        ):
            queue_worker.consume_queue(
                "observer", "observation-mesh", once=True, start="/explicit/start"
            )

        find_root.assert_called_once_with("/explicit/start")


if __name__ == "__main__":
    unittest.main(verbosity=2)
