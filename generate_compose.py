#!/usr/bin/env python3
"""Dynamic Compose & Container Harness Generation for the Recursive Field.

Inspects the live field topology (agents, meshes, gateways) and emits a
location-agnostic ``docker-compose.yml`` powered by dynamic variable
interpolation (``${FIELD_ROOT}``, ``${IMAGE_NAME}``).

Usage:
    python3 generate_compose.py [--out docker-compose.yml] [--port-base 44000]

Exit codes:
    0  compose spec generated successfully
    1  field root not found or runtime error
    2  integrity / validation failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the script's own directory is importable when invoked from
# a different working directory.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from find_root import find_root  # noqa: E402

MARKER_FILENAME = ".recursive-field-root"
ENV_FILENAME = "field_env.json"
COMPOSE_VERSION = "3.8"
DEFAULT_IMAGE = "agent0ai/agent-zero:latest"
LIBRARY_ENV_VAR = "LIBRARY"
DEFAULT_LIBRARY = "recursive-field"
DEFAULT_KNOWLEDGE_DIR = ""


# ─── YAML helpers (manual, no external dependency) ───────────────────


def _yaml_scalar(val: str | int | float | bool | None) -> str:
    """Serialize a scalar value to a YAML-safe string."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val)
    # Quote strings that contain special characters.
    if any(c in s for c in [":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|", ">", "'", '"', "\n", "@"]):
        return f'"{s.replace(chr(34), chr(92) + chr(34))}"'
    return s


def _yaml_dump(data, indent: int = 0) -> str:
    """Recursively dump Python data to YAML text."""
    lines: list[str] = []
    pad = " " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{pad}{key}:")
                lines.append(_yaml_dump(value, indent + 2))
            elif isinstance(value, list):
                lines.append(f"{pad}{key}:")
                for item in value:
                    if isinstance(item, (dict, list)):
                        lines.append(_yaml_dump(item, indent + 2).lstrip())
                    else:
                        lines.append(f"{pad}- {_yaml_scalar(item)}")
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(value)}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                sub = _yaml_dump(item, indent + 2)
                lines.append(f"{pad}- " + sub.lstrip())
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
    else:
        lines.append(f"{pad}{_yaml_scalar(data)}")

    return "\n".join(lines)


def _dict_to_yaml(data: dict) -> str:
    """Convert a dict to a complete YAML document string."""
    return _yaml_dump(data) + "\n"


# ─── JSON helpers ───────────────────────────────────────────────────


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ─── Topology scanning ──────────────────────────────────────────────


def _scan_agents(agents_dir: Path) -> list[dict]:
    agents: list[dict] = []
    if not agents_dir.is_dir():
        return agents
    for path in sorted(agents_dir.iterdir()):
        if not path.is_dir():
            continue
        identity_path = path / "identity.json"
        if not identity_path.is_file():
            continue
        identity = _read_json(identity_path)
        agents.append({
            "slug": identity.get("slug", path.name),
            "agent_id": identity.get("agent_id", ""),
            "role": identity.get("role", ""),
            "dir": path,
        })
    return agents


def _scan_meshes(mesh_dir: Path) -> list[dict]:
    meshes: list[dict] = []
    if not mesh_dir.is_dir():
        return meshes
    for path in sorted(mesh_dir.iterdir()):
        if not path.is_dir():
            continue
        channel_path = path / "channel.json"
        if not channel_path.is_file():
            continue
        channel = _read_json(channel_path)
        endpoints = channel.get("endpoints", [])
        meshes.append({
            "slug": channel.get("slug", path.name),
            "mesh_id": channel.get("mesh_id", ""),
            "channel_type": channel.get("channel_type", ""),
            "endpoints": endpoints,
            "dir": path,
        })
    return meshes


def _scan_gateways(gw_dir: Path) -> list[dict]:
    gateways: list[dict] = []
    if not gw_dir.is_dir():
        return gateways
    for path in sorted(gw_dir.iterdir()):
        if not path.is_dir():
            continue
        manifest_path = path / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        gateways.append({
            "slug": manifest.get("slug", path.name),
            "gateway_id": manifest.get("gateway_id", ""),
            "target_type": manifest.get("target_type", ""),
            "target_slug": manifest.get("target_slug", ""),
            "gateway_type": manifest.get("gateway_type", ""),
            "status": manifest.get("status", ""),
            "dir": path,
        })
    return gateways


# ─── .env generation ───────────────────────────────────────────────


def _generate_env(root: Path, port_base: int, image_name: str, library: str = DEFAULT_LIBRARY, knowledge_dir: str = DEFAULT_KNOWLEDGE_DIR) -> str:
    return (
        f"# Recursive Field — auto-generated environment\n"
        f"# Do not commit secrets here.\n"
        f"\n"
        f"LIBRARY={library}\n"
        f"KNOWLEDGE_DIR={knowledge_dir}\n"
        f"FIELD_ROOT={root}\n"
        f"PORT_BASE={port_base}\n"
        f"IMAGE_NAME={image_name}\n"
    )


# ─── Nginx config for HTTP gateways ────────────────────────────────


def _generate_nginx_conf(gateway_slug: str, mesh_slug: str, agents: list[dict]) -> str:
    """Generate an nginx reverse-proxy config for a mesh HTTP gateway."""
    upstream_servers = "\n".join(
        f"    server ${{{LIBRARY_ENV_VAR}}}-{a['slug']}:8000;"
        for a in agents
    )
    return (
        f"# Auto-generated nginx config for gateway: {gateway_slug}\n"
        f"# Targets mesh: {mesh_slug}\n"
        f"\n"
        f"events {{}}\n"
        f"\n"
        f"http {{\n"
        f"  upstream mesh_backend {{\n"
        f"{upstream_servers}\n"
        f"  }}\n"
        f"\n"
        f"  server {{\n"
        f"    listen 80;\n"
        f"\n"
        f"    location / {{\n"
        f"      proxy_pass http://mesh_backend;\n"
        f"      proxy_set_header Host $host;\n"
        f"      proxy_set_header X-Real-IP $remote_addr;\n"
        f"      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
        f"    }}\n"
        f"  }}\n"
        f"}}\n"
    )


# ─── Compose spec generation ───────────────────────────────────────


def _build_agent_service(
    agent: dict,
    port_base: int,
    mesh_bindings: list[dict],
) -> dict:
    """Build a single agent service definition."""
    slug = agent["slug"]
    service_name = f"${{{LIBRARY_ENV_VAR}}}-{slug}"

    volumes = [
        f"${{FIELD_ROOT}}/agents/{slug}:/a0/agents/{slug}:rw",
        f"${{FIELD_ROOT}}/agents/{slug}/memory:/a0/memory:rw",
        f"${{FIELD_ROOT}}/agents/{slug}/observations:/a0/observations:rw",
        f"${{FIELD_ROOT}}/tmp/{ENV_FILENAME}:/a0/tmp/{ENV_FILENAME}:ro",
    ]

    # Add mesh queue bindings.
    for mb in mesh_bindings:
        mesh_slug = mb["slug"]
        volumes.append(
            f"${{FIELD_ROOT}}/mesh/{mesh_slug}/queue.jsonl:"
            f"/a0/mesh/{mesh_slug}/queue.jsonl:rw"
        )

    environment = [
        f"FIELD_ROOT=${{FIELD_ROOT}}",
        f"AGENT_SLUG={slug}",
        f"AGENT_ID={agent['agent_id']}",
    ]

    service: dict = {
        "image": "${IMAGE_NAME}",
        "container_name": service_name,
        "environment": environment,
        "volumes": volumes,
        "networks": ["field-bridge"],
        "restart": "unless-stopped",
    }

    # Assign SSH port (container port 22 → host port BASE+22).
    ssh_port = port_base + 22
    service["ports"] = [f"{ssh_port}:22"]

    return service


def _build_nginx_service(
    gateway: dict,
    port_base: int,
    target_agents: list[dict],
    root: Path,
) -> dict:
    """Build an nginx ingress service for an HTTP/API gateway."""
    gw_slug = gateway["slug"]
    service_name = f"${{{LIBRARY_ENV_VAR}}}-{gw_slug}"

    # Generate nginx.conf into the gateway directory.
    nginx_conf = _generate_nginx_conf(
        gw_slug,
        gateway["target_slug"],
        target_agents,
    )
    nginx_path = gateway["dir"] / "nginx.conf"
    nginx_path.write_text(nginx_conf, encoding="utf-8")

    http_port = port_base + 80

    return {
        "image": "nginx:latest",
        "container_name": service_name,
        "ports": [f"{http_port}:80"],
        "volumes": [
            f"${{FIELD_ROOT}}/gateways/{gw_slug}/nginx.conf:"
            f"/etc/nginx/nginx.conf:ro",
        ],
        "networks": ["field-bridge"],
        "restart": "unless-stopped",
        "depends_on": [
            f"${{{LIBRARY_ENV_VAR}}}-{a['slug']}" for a in target_agents
        ],
    }


def _build_compose_spec(
    root: Path,
    agents: list[dict],
    meshes: list[dict],
    gateways: list[dict],
    port_base: int,
) -> dict:
    """Build the full docker-compose spec as a Python dict."""
    # Build agent→mesh binding index.
    agent_mesh_bindings: dict[str, list[dict]] = {a["slug"]: [] for a in agents}
    for mesh in meshes:
        for ep in mesh["endpoints"]:
            ep_slug = ep.get("slug", "")
            if ep_slug in agent_mesh_bindings:
                agent_mesh_bindings[ep_slug].append(mesh)

    services: dict[str, dict] = {}

    # Agent services — each gets a unique SSH port offset by index.
    for idx, agent in enumerate(agents):
        slug = agent["slug"]
        agent_port_base = port_base + idx * 100
        service = _build_agent_service(
            agent, agent_port_base, agent_mesh_bindings.get(slug, [])
        )
        services[f"agent-{slug}"] = service

    # Gateway services (nginx for HTTP/API).
    for gw in gateways:
        if gw["gateway_type"] in ("http", "api"):
            # Determine target agents for the mesh.
            target_agents: list[dict] = []
            if gw["target_type"] == "mesh":
                mesh = next(
                    (m for m in meshes if m["slug"] == gw["target_slug"]),
                    None,
                )
                if mesh:
                    for ep in mesh["endpoints"]:
                        ep_slug = ep.get("slug", "")
                        agent = next(
                            (a for a in agents if a["slug"] == ep_slug),
                            None,
                        )
                        if agent:
                            target_agents.append(agent)
            elif gw["target_type"] == "agent":
                agent = next(
                    (a for a in agents if a["slug"] == gw["target_slug"]),
                    None,
                )
                if agent:
                    target_agents = [agent]

            nginx_service = _build_nginx_service(
                gw, port_base, target_agents, root
            )
            services[f"nginx-{gw['slug']}"] = nginx_service

    spec = {
        "version": COMPOSE_VERSION,
        "services": services,
        "networks": {
            "field-bridge": {
                "driver": "bridge",
            },
        },
    }

    return spec


# ─── Main ──────────────────────────────────────────────────────────


def generate_compose(
    out_path: str | None = None,
    port_base: int = 44000,
    image_name: str = DEFAULT_IMAGE,
    start: str | os.PathLike[str] | None = None,
) -> dict:
    """Generate .env and docker-compose.yml at the field root.

    Args:
        out_path: Output path for docker-compose.yml (default: field root).
        port_base: Base port for host port derivation.
        image_name: Docker image name for agent services.
        start: Directory to begin root discovery from.

    Returns:
        A dict with generation metadata.
    """
    root = find_root(start)
    if root is None:
        raise RuntimeError(
            "Could not locate field root: no .recursive-field-root marker "
            "found in the current directory or any ancestor."
        )

    # Verify env file.
    env_path = root / "tmp" / ENV_FILENAME
    if not env_path.is_file():
        raise FileNotFoundError(
            f"Runtime environment file not found: {env_path}. "
            "Run init_field_environment.py first."
        )

    # Scan topology.
    agents = _scan_agents(root / "agents")
    meshes = _scan_meshes(root / "mesh")
    gateways = _scan_gateways(root / "gateways")

    # Read LIBRARY and KNOWLEDGE_DIR from environment or .env file.
    library = os.environ.get("LIBRARY", DEFAULT_LIBRARY)
    knowledge_dir = os.environ.get("KNOWLEDGE_DIR", DEFAULT_KNOWLEDGE_DIR)

    # Generate .env.
    env_content = _generate_env(root, port_base, image_name, library, knowledge_dir)
    env_file_path = root / ".env"
    env_file_path.write_text(env_content, encoding="utf-8")

    # Generate docker-compose.yml.
    spec = _build_compose_spec(root, agents, meshes, gateways, port_base)
    compose_text = _dict_to_yaml(spec)

    compose_path = Path(out_path) if out_path else root / "docker-compose.yml"
    if not compose_path.is_absolute():
        compose_path = root / compose_path
    compose_path.write_text(compose_text, encoding="utf-8")

    # Count services.
    service_names = list(spec["services"].keys())
    # Service names use ${LIBRARY}- prefix via env var interpolation.
    # Count by checking service image type.
    agent_services = [n for n in service_names if spec["services"][n].get("image", "") == "${IMAGE_NAME}"]
    nginx_services = [n for n in service_names if spec["services"][n].get("image", "") == "nginx:latest"]

    # List generated nginx configs.
    nginx_configs = []
    for gw in gateways:
        if gw["gateway_type"] in ("http", "api"):
            nginx_configs.append(str(gw["dir"] / "nginx.conf"))

    return {
        "field_root": str(root),
        "env_path": str(env_file_path),
        "compose_path": str(compose_path),
        "port_base": port_base,
        "image_name": image_name,
        "total_services": len(service_names),
        "agent_services": len(agent_services),
        "nginx_services": len(nginx_services),
        "service_names": service_names,
        "nginx_configs": nginx_configs,
    }


def _print_result(result: dict) -> None:
    print(f"Field Root: {result['field_root']}")
    print(f".env: {result['env_path']}")
    print(f"Compose: {result['compose_path']}")
    print(f"Port Base: {result['port_base']}")
    print(f"Image: {result['image_name']}")
    print(
        f"\nServices ({result['total_services']}): "
        f"{result['agent_services']} agents, "
        f"{result['nginx_services']} nginx"
    )
    for name in result["service_names"]:
        print(f"  - {name}")
    if result["nginx_configs"]:
        print(f"\nNginx configs generated:")
        for cfg in result["nginx_configs"]:
            print(f"  - {cfg}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dynamic Compose & Container Harness Generation"
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output path for docker-compose.yml (default: field root)",
    )
    parser.add_argument(
        "--port-base",
        type=int,
        default=44000,
        help="Base port for host port derivation (default: 44000)",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=DEFAULT_IMAGE,
        help=f"Docker image name (default: {DEFAULT_IMAGE})",
    )
    args = parser.parse_args(argv)

    try:
        result = generate_compose(
            out_path=args.out,
            port_base=args.port_base,
            image_name=args.image,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
