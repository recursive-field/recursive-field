# Effective-Formation Observer

## Purpose

- Own the first construction slice: a public-safe, read-only, non-authoritative observer for one bounded Agent Zero context.
- Keep sanitized fixture interpretation separate from live runtime adapters and from any future authority or enforcement mechanism.

## Ownership

- `effective_formation_observer.py` owns strict fixture validation, deterministic winner/shadow classification, policy-boundary reporting, and JSON rendering.
- `fixtures/` owns content-free test inputs only.
- `tests/` owns behavioral acceptance checks for this observer boundary.

## Local Contracts

- Accept only the documented content-free input shape; reject unknown fields rather than silently carrying private content.
- Treat context, project, and profile references as mutable selectors, never identity.
- Report selection, projection, enforcement, authority, and consequence evidence separately.
- Never read Agent Zero private runtime state, secrets, participant content, network services, or live infrastructure.
- Never mutate the observed formation. The command writes only to standard output.
- Never describe a winner, policy decision, hash, or successful run as trust, permission, continuity, readiness, or authority.
- Keep output deterministic for unchanged input.

## Work Guidance

- Prefer standard-library Python and narrow pure functions.
- Add a runtime adapter only after its disclosure boundary and removal path have independent acceptance evidence.
- Keep fixtures synthetic and free of real paths, hosts, accounts, credentials, participant names, and private topology.

## Verification

Run from the repository root:

```bash
python -m unittest discover -s observer/tests -v
python observer/effective_formation_observer.py observer/fixtures/bounded_context.json
```

Also verify that the CLI leaves the fixture directory unchanged and that generated output contains no input content fields or authority claims.

## Child DOX Index

No child ownership boundaries exist yet.
