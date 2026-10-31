"""Expose the Recursive Field contract to Agent Zero's generic persistence owner."""

from pathlib import Path

from helpers.extension import Extension


class RecursiveFieldTurnObligationContract(Extension):
    def execute(self, data=None, **kwargs):
        if not isinstance(data, dict):
            raise ValueError("turn_obligation_contract requires mutable data")
        if data.get("adapter") is not None:
            raise ValueError("multiple turn-obligation contract adapters are active")
        root = Path(__file__).resolve().parents[4]
        from importlib.util import module_from_spec, spec_from_file_location
        import sys

        module_name = "recursive_field_turn_obligation_adapter"
        module = sys.modules.get(module_name)
        if module is None:
            spec = spec_from_file_location(module_name, root / "turn_obligation_adapter.py")
            if spec is None or spec.loader is None:
                raise ImportError("turn_obligation_adapter.py cannot be loaded")
            module = module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except BaseException:
                sys.modules.pop(module_name, None)
                raise
        data["adapter"] = module.RecursiveFieldTurnObligationAdapter(root)
