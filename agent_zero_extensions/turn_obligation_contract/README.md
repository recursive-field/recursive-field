# Recursive Field turn-obligation adapter hook

This hook is installation source, not an active runtime copy. When installed under `.a0proj/extensions/python/turn_obligation_contract/`, it supplies the project-owned `RecursiveFieldTurnObligationAdapter` to Agent Zero's framework-owned persistence layer.

The hook rejects multiple adapters and loads `turn_obligation_adapter.py` from the containing project root. Agent Zero owns chat-coordinate locking, immutable generation files, atomic heads, and fsync; Recursive Field owns schema 1.1.0 semantics, lineage validation, typed evidence, and protocol-reflex anti-recursion.
