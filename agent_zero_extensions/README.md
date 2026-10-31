# Agent Zero project-extension source

This directory contains tracked, installable source for Recursive Field project extensions. It is not an active Agent Zero extension directory.

## Turn-obligation contract adapter

`turn_obligation_contract/_10_recursive_field.py` registers `turn_obligation_adapter.py` at Agent Zero's generic `turn_obligation_contract` extension point. To activate it in a later deployment phase, copy that file to:

```text
.a0proj/extensions/python/turn_obligation_contract/_10_recursive_field.py
```

Activation or reload is deliberately outside the local integration phase. The tracked hook resolves the field root relative to its installed `.a0proj` location and never hard-codes `/a0/usr/projects/recursive-field`.
