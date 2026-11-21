from importlib import import_module
from types import ModuleType

from .errors import AppError


def require_module(path: str) -> ModuleType:
    """Load a team module at its handoff point while branches are being integrated."""
    try:
        return import_module(path)
    except ModuleNotFoundError as exc:
        if exc.name and (exc.name == path or path.startswith(f"{exc.name}.")):
            module = path.split(".")[2]
            raise AppError("MODULE_NOT_READY", f"The {module} module is not available yet.", 503) from exc
        raise
