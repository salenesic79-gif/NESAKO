# EKSPERIMENTALNO: Ovaj modul nije integrisan u stabilan workflow!
"""
Auto-plugin loader for ai_assistant.plugins package.
Discovers modules under ai_assistant/plugins/ that expose a callable `run(**kwargs)`.
"""
import importlib
import pkgutil
from types import ModuleType
from typing import List, Dict, Any


def discover_plugins(package: ModuleType) -> List[Dict[str, Any]]:
    """Discover plugin modules inside the given package.

    A plugin is any module that defines a top-level callable `run(**kwargs)`.

    Returns a list of dicts with keys: name, module, has_run.
    """
    plugins = []
    try:
        for loader, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            try:
                full_name = f"{package.__name__}.{module_name}"
                mod = importlib.import_module(full_name)
                has_run = callable(getattr(mod, 'run', None))
                plugins.append({
                    'name': module_name,
                    'module': mod,
                    'has_run': has_run,
                })
            except Exception as e:
                # Skip faulty modules, but keep discovery robust
                plugins.append({
                    'name': module_name,
                    'module': None,
                    'has_run': False,
                    'error': str(e),
                })
    except Exception:
        # If discovery fails entirely, return empty list (non-fatal)
        return []
    return plugins
