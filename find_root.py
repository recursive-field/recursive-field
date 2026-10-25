#!/usr/bin/env python3
"""Root resolver for the Recursive Field.

Traverses upward from the current working directory (or a given start path)
until it locates a `.recursive-field-root` marker file, then prints the
absolute path of the directory containing that marker.

Usage:
    python find_field_root.py [start_path]

Exit codes:
    0  root found and printed to stdout
    1  root not found
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER_FILENAME = ".recursive-field-root"


def find_root(start: str | os.PathLike[str] | None = None) -> Path | None:
    """Return the nearest ancestor directory containing the marker file.

    Args:
        start: Directory to begin searching from. Defaults to the current
            working directory.

    Returns:
        The absolute :class:`~pathlib.Path` of the directory containing the
        marker, or ``None`` if no marker is found before the filesystem root.
    """
    start_path: Path = Path(start).resolve() if start else Path.cwd()

    for candidate in [start_path, *start_path.parents]:
        if (candidate / MARKER_FILENAME).is_file():
            return candidate

    return None


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    start = argv[0] if argv else None

    root = find_root(start)
    if root is None:
        print("No .recursive-field-root marker found.", file=sys.stderr)
        return 1

    print(str(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
