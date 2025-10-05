from typing import Callable, Dict, Any, List
from dataclasses import dataclass

@dataclass
class ModuleAction:
    name: str
    view: Callable[..., Any]  # Django view callable (request -> JsonResponse)
    description: str = ""

class BaseAIModule:
    """Base class for NESAKO AI modules."""
    name: str = "unnamed"

    def routes(self) -> Dict[str, ModuleAction]:
        """Return a dict of action_name -> ModuleAction."""
        return {}

    def manifest(self) -> Dict[str, Any]:
        actions = self.routes()
        return {
            "name": self.name,
            "actions": [
                {"name": a.name, "description": a.description}
                for a in actions.values()
            ],
        }

# Helper responses (avoid importing Django here)
def json_ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", **data}

def json_err(message: str, **meta) -> Dict[str, Any]:
    return {"status": "error", "error": message, **meta}
