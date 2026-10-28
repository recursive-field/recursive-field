# Agent Zero Plugin Packages

This directory is the Recursive Field repository's tracked source boundary for installable Agent Zero plugins. It is distinct from the live Agent Zero runtime tree:

- tracked package source: `agent_zero_plugins/<plugin>/`
- runtime installation: `/a0/usr/plugins/<plugin>/`

The runtime tree is ignored Agent Zero user state and is not part of this repository. Do not symlink plugin imports across these boundaries; user plugins use `usr.plugins.<name>...` only after installation under `/a0/usr/plugins`.

## Continuation Reflex

`continuation_reflex/` packages the fail-closed continuation adapter. Its current implementation validates explicit formation handoffs but deliberately does not claim or fire them because the current Agent Zero runtime has no native typed-system/protocol, exactly-one-model-turn entrypoint that avoids creating a user-history message.

### Install or update later

Do not copy over a running Agent Zero instance. With Agent Zero stopped, copy the package into the user-plugin root, then start Agent Zero normally so the standard plugin lifecycle discovers it:

```bash
cd /a0/usr/projects/recursive-field
rm -rf /a0/usr/plugins/continuation_reflex
mkdir -p /a0/usr/plugins/continuation_reflex
cp -a agent_zero_plugins/continuation_reflex/. /a0/usr/plugins/continuation_reflex/
find /a0/usr/plugins/continuation_reflex -type d -name __pycache__ -prune -exec rm -rf {} +
```

Alternatively, archive the **contents** of `agent_zero_plugins/continuation_reflex/` at the ZIP root and install it through Agent Zero's plugin manager. The package has no dependencies or external services; lifecycle hooks are idempotent no-ops.

The default configuration remains inert (`enabled: false`). Enabling it before the missing framework entrypoint exists only performs read-only inspection and reports the blocked boundary; it does not start a turn.
