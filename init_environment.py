#!/usr/bin/env python3
"""Environment initialization for the Recursive Field.

Discovers the field root via ``find_root``, validates the genesis
marker, provisions the core primitive/state directories, and writes a
localized runtime context file (``tmp/field_env.json``).

Usage:
    python init_environment.py [start_path]

Exit codes:
    0  environment initialized successfully
    1  field root not found
    2  genesis marker validation failed
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the script's own directory is importable when invoked from
# a different working directory.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from find_root import find_root  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
EXPECTED_SCHEMA_VERSION = "1.0.0"

REQUIRED_DIRS = [
    "agents",    # identity & observation
    "mesh",      # connectivity
    "gateways",  # interfaces
    "state",     # durable state & history
    "tmp",        # runtime scratch space
]


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with timezone offset."""
    return datetime.now(timezone.utc).isoformat()


def _read_env_file(path: Path) -> dict[str, str]:
    """Read simple key/value assignments without executing shell syntax."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[:1] == value[-1:] and value.startswith(("'", '"')):
            value = value[1:-1]
        if key:
            values[key] = value

    return values


def validate_marker(marker_path: Path) -> dict:
    """Read and validate the genesis marker file.

    Args:
        marker_path: Absolute path to the ``.recursive-field-root`` file.

    Returns:
        Parsed marker dict on success.

    Raises:
        ValueError: If the file is missing, not valid JSON, or missing
            required fields (``genesis_uuid``, ``schema_version``).
    """
    if not marker_path.is_file():
        raise ValueError(f"Marker file not found: {marker_path}")

    data = json.loads(marker_path.read_text(encoding="utf-8"))

    if "genesis_uuid" not in data:
        raise ValueError("Marker is missing required field: genesis_uuid")
    if "schema_version" not in data:
        raise ValueError("Marker is missing required field: schema_version")
    if data["schema_version"] != EXPECTED_SCHEMA_VERSION:
        raise ValueError(
            f"Schema version mismatch: expected {EXPECTED_SCHEMA_VERSION!r}, "
            f"got {data['schema_version']!r}"
        )

    return data


def init_environment(start: str | os.PathLike[str] | None = None) -> dict:
    """Discover the field root, provision directories, and write context.

    Args:
        start: Directory to begin root discovery from. Defaults to cwd.

    Returns:
        The runtime context dict that was written to ``tmp/field_env.json``.

    Raises:
        RuntimeError: If the field root cannot be discovered.
        ValueError: If the genesis marker fails validation.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    marker_path = root / MARKER_FILENAME
    marker_data = validate_marker(marker_path)

    # Provision directories.
    for dir_name in REQUIRED_DIRS:
        (root / dir_name).mkdir(parents=True, exist_ok=True)

    # Resolve identity and knowledge from process environment, then the
    # discovered root's .env file, then stable defaults. FIELD_ROOT remains
    # marker-derived so configuration cannot bypass root discovery.
    env_file = _read_env_file(root / ".env")
    library = os.environ.get("LIBRARY", env_file.get("LIBRARY", "recursive-field"))
    knowledge_dir = os.environ.get(
        "KNOWLEDGE_DIR", env_file.get("KNOWLEDGE_DIR", "")
    )

    # Generate runtime context.
    context = {
        "field_root": str(root),
        "genesis_uuid": marker_data["genesis_uuid"],
        "library": library,
        "knowledge_dir": knowledge_dir,
        "agents_dir": str(root / "agents"),
        "mesh_dir": str(root / "mesh"),
        "gateways_dir": str(root / "gateways"),
        "state_dir": str(root / "state"),
        "initialized_at": _utc_now_iso(),
    }

    context_path = root / "tmp" / "field_env.json"
    context_path.write_text(
        json.dumps(context, indent=2) + "\n",
        encoding="utf-8",
    )

    return context


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    start = argv[0] if argv else None

    try:
        context = init_environment(start)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(context, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
