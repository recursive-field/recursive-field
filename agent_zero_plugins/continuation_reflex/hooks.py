"""Lifecycle hooks for the dependency-free local plugin."""


def install() -> None:
    """No dependencies or external resources are required."""


def pre_update() -> None:
    """No plugin-owned process is started by this package."""


def uninstall() -> None:
    """No external resources exist to remove."""
