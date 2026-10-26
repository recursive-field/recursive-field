# systemd queue worker templates

These source templates render one bounded queue worker and one persistent,
approximately five-second calendar timer for a single agent/mesh pair. A
brand-neutral `docker.service` drop-in also makes the exact field-root mount a
prerequisite for Docker startup, protecting auto-restarted bind-mounted
containers from a fallback root-disk directory. These units are not additional
Python scripts.

## Deployment substitutions

Render every placeholder to a deployment-specific literal:

| Placeholder | Example | Contract |
| --- | --- | --- |
| `@FIELD_ROOT@` | `/mnt/field` | Absolute, canonical path which is itself an active mount point |
| `@AGENT_SLUG@` | `observer` | Existing recipient slug |
| `@MESH_SLUG@` | `observation-mesh` | Existing mesh slug |
| `@SERVICE_UNIT@` | `queue-worker-observer-observation-mesh.service` | Installed service basename including `.service` |
| `@LOCK_RUNTIME_DIR@` | `queue-worker-observer-observation-mesh` | Safe single directory name created below `/run` |
| `@LOCK_FILE@` | `consume.lock` | Safe single file name within the runtime directory |

`@FIELD_ROOT@` must be replaced everywhere by the exact deployed field root,
not by a parent mount, symlink, repository-build path, or fallback directory.
The worker has both `RequiresMountsFor=` and a `mountpoint --quiet`
`ExecCondition`; the Docker drop-in gives `docker.service` the same exact mount
prerequisite. Thus Docker cannot start auto-restarted bind-mounted containers,
and the worker cannot run, when the required detachable storage mount fails. If
the field is a subdirectory of a larger mounted filesystem, arrange a mount or
bind mount at the field root itself before enabling these units.

The templates intentionally run the worker as `root` for the first deployment.
The current durable runtime files are root-owned and `setfacl` is unavailable;
changing `User=`, ownership, or file modes here would silently alter the existing
persistence contract. Root instead runs inside a strongly restricted service
mount/network namespace: no capabilities, no privilege gain, private temporary
and device trees, strict system/home protection, no IP networking, and write
access limited to the exact field root plus its private lock directory.

## Render and validate

Choose values whose paths/names contain no whitespace, `@`, or `|`, then stage
the rendered units before installing them:

```bash
cd /path/to/field-source
FIELD_ROOT=/exact/active/field-mount
AGENT_SLUG=observer
MESH_SLUG=observation-mesh
UNIT_STEM="queue-worker-${AGENT_SLUG}-${MESH_SLUG}"
SERVICE_UNIT="${UNIT_STEM}.service"
LOCK_RUNTIME_DIR="${UNIT_STEM}"
LOCK_FILE=consume.lock
STAGE="$(mktemp -d)"

[ "$(readlink -f -- "$FIELD_ROOT")" = "$FIELD_ROOT" ]
mountpoint --quiet -- "$FIELD_ROOT"

render() {
  sed \
    -e "s|@FIELD_ROOT@|${FIELD_ROOT}|g" \
    -e "s|@AGENT_SLUG@|${AGENT_SLUG}|g" \
    -e "s|@MESH_SLUG@|${MESH_SLUG}|g" \
    -e "s|@SERVICE_UNIT@|${SERVICE_UNIT}|g" \
    -e "s|@LOCK_RUNTIME_DIR@|${LOCK_RUNTIME_DIR}|g" \
    -e "s|@LOCK_FILE@|${LOCK_FILE}|g" \
    "$1" > "$2"
}

render systemd/queue-worker.service.in "$STAGE/$SERVICE_UNIT"
render systemd/queue-worker.timer.in "$STAGE/${UNIT_STEM}.timer"
render systemd/docker.service.d/field-root.conf.in \
  "$STAGE/docker-field-root.conf"
! grep -R '@[A-Z_][A-Z_]*@' "$STAGE"
systemd-analyze verify "$STAGE/$SERVICE_UNIT" "$STAGE/${UNIT_STEM}.timer"
```

Inspect the staged output. In particular, verify that `RequiresMountsFor=`,
`ExecCondition=`, `Environment=FIELD_ROOT=`, `ExecStart=`, and
`ReadWritePaths=` all contain the same exact field-root coordinate.

## Install Docker boot safety

Install the drop-in before relying on Docker auto-restart. A daemon reload makes
it effective for the next Docker start; it does not restart or interrupt an
already-running daemon.

```bash
install -d -o root -g root -m 0755 /etc/systemd/system/docker.service.d
install -o root -g root -m 0644 "$STAGE/docker-field-root.conf" \
  /etc/systemd/system/docker.service.d/field-root.conf
systemctl daemon-reload
systemctl cat docker.service
```

Do not restart Docker merely to test the dependency outside an approved outage
window. On the next boot or intentional daemon start, failure of the required
mount prevents the entire Docker daemon from starting, so this host-wide guard
protects every auto-restarted container at the cost of delaying unrelated
containers too. The field mount must not itself depend on Docker.

## Install the queue worker

```bash
install -o root -g root -m 0644 "$STAGE/$SERVICE_UNIT" \
  "/etc/systemd/system/$SERVICE_UNIT"
install -o root -g root -m 0644 "$STAGE/${UNIT_STEM}.timer" \
  "/etc/systemd/system/${UNIT_STEM}.timer"
systemctl daemon-reload
systemctl enable --now "${UNIT_STEM}.timer"
systemctl status "${UNIT_STEM}.timer" --no-pager
```

The timer follows wall-clock boundaries at seconds `00/5`. `Persistent=true`
causes one immediate, coalesced catch-up activation after downtime if at least
one boundary was missed; it does not replay every missed interval. The next
regular boundary can follow that catch-up by less than five seconds. The
oneshot worker processes at most one task, systemd does not reactivate it while
it remains active, and `flock` prevents overlapping execution from any other
activation source. Lock contention (75) and security lockdown (4) are normal
successful unit outcomes. Output and errors go to journald under the rendered
service unit identifier. Inspect with:

```bash
journalctl -u "$SERVICE_UNIT" -u "${UNIT_STEM}.timer"
```

## Recover after a blocked Docker start

A missing or failed detachable mount now leaves Docker stopped; container restart
policies cannot take effect until the dependency is healthy. Repair or reattach
the storage first, then verify both the mount boundary and field identity before
starting Docker:

```bash
MOUNT_UNIT="$(systemd-escape --path --suffix=mount "$FIELD_ROOT")"
systemctl reset-failed "$MOUNT_UNIT" docker.service
systemctl start "$MOUNT_UNIT"
mountpoint --quiet -- "$FIELD_ROOT"
test -f "$FIELD_ROOT/.recursive-field-root"
systemctl start docker.service
```

If the mount cannot be recovered, keep Docker stopped while deciding how to
restore the volume or reconfigure affected bind mounts. Removing the guard and
starting Docker while the fallback directory is exposed recreates the failure
mode this drop-in prevents.

## Roll back

The scheduler can be removed without changing ownership or deleting queue,
cursor, claim, result, or other durable field state:

```bash
systemctl disable --now "${UNIT_STEM}.timer"
systemctl stop "$SERVICE_UNIT" 2>/dev/null || true
rm -f "/etc/systemd/system/${UNIT_STEM}.timer" \
      "/etc/systemd/system/$SERVICE_UNIT"
systemctl daemon-reload
systemctl reset-failed "$SERVICE_UNIT" 2>/dev/null || true
```

Remove the Docker guard only after the exact mount is healthy or when explicitly
accepting the risk of Docker starting against the fallback directory. Reloading
configuration does not restart a running daemon:

```bash
rm -f /etc/systemd/system/docker.service.d/field-root.conf
rmdir --ignore-fail-on-non-empty /etc/systemd/system/docker.service.d
systemctl daemon-reload
```
