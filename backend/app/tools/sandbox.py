"""
Restricted Python code sandbox for LLM-generated analysis code.

Provides a ``run_code`` function that executes arbitrary Python in a
controlled environment with:
- Whitelist-only imports (no system/network modules)
- Thread-based timeout (auto-kills infinite loops)
- Stdout capture (returned as part of the result)
- Pre-loaded ``engine`` (QueryEngine) and ``pd`` / ``np`` for data analysis
- Output size limits
"""

from __future__ import annotations

import io
import threading
import traceback
from contextlib import redirect_stdout
from typing import Any

from app.tools.engine import QueryEngine
from app.tools.models import (
    HighValueParams,
    SearchParams,
    SqlQueryParams,
    SummaryParams,
    SuspiciousPatternParams,
)

# ---------------------------------------------------------------------------
# Safe builtins whitelist
# ---------------------------------------------------------------------------

_SAFE_BUILTINS: dict[str, Any] = {
    # Constants
    "True": True,
    "False": False,
    "None": None,
    # Core types & factories
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "bytes": bytes,
    "chr": chr,
    "complex": complex,
    "dict": dict,
    "dir": dir,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "getattr": getattr,
    "hasattr": hasattr,
    "hash": hash,
    "hex": hex,
    "id": id,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "object": object,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "super": super,
    "tuple": tuple,
    "type": type,
    "vars": vars,
    "zip": zip,
    # Exceptions
    "ArithmeticError": ArithmeticError,
    "AssertionError": AssertionError,
    "AttributeError": AttributeError,
    "Exception": Exception,
    "IndexError": IndexError,
    "KeyError": KeyError,
    "LookupError": LookupError,
    "OverflowError": OverflowError,
    "RuntimeError": RuntimeError,
    "StopIteration": StopIteration,
    "TypeError": TypeError,
    "ValueError": ValueError,
    "ZeroDivisionError": ZeroDivisionError,
}

# ---------------------------------------------------------------------------
# Module whitelist
# ---------------------------------------------------------------------------

_ALLOWED_MODULES: dict[str, str | None] = {
    # Third-party data-science libs (if installed in the environment)
    "pandas": "pd",
    "numpy": "np",
    "duckdb": None,
    # Standard library (safe subset)
    "collections": None,
    "datetime": None,
    "decimal": None,
    "functools": None,
    "itertools": None,
    "json": None,
    "math": None,
    "random": None,
    "re": None,
    "statistics": None,
    "string": None,
    "typing": None,
}

# ---------------------------------------------------------------------------
# Custom import hook
# ---------------------------------------------------------------------------

_IMPORT_ERROR_MSG = (
    "Module '{name}' is not allowed in the code sandbox. "
    "Allowed modules: {allowed}"
)


class _RestrictedImporter:
    """Replaces ``__import__`` to enforce the module whitelist."""

    def __init__(self, allowed: dict[str, str | None]) -> None:
        self._allowed = allowed
        # Use getattr because __builtins__ may be a module (not a dict) at module scope
        bltins = __builtins__
        if isinstance(bltins, dict):
            self._original_import = bltins["__import__"]
        else:
            self._original_import = getattr(bltins, "__import__")

    def __call__(
        self,
        name: str,
        globals: Any = None,
        locals: Any = None,
        fromlist: Any = None,
        level: int = 0,
    ) -> Any:
        # Relative imports are always blocked
        if level != 0:
            raise ImportError(
                f"Relative imports are not allowed in the code sandbox."
            )
        # Permit explicit sub-module access (e.g. `from json.decoder import ...`)
        base = name.split(".")[0]
        if base not in self._allowed:
            raise ImportError(
                _IMPORT_ERROR_MSG.format(
                    name=name,
                    allowed=", ".join(sorted(self._allowed)),
                )
            )
        module = self._original_import(name, globals, locals, fromlist, level)
        # Optionally assign a short alias (e.g. "pd" for "pandas")
        alias = self._allowed[base]
        if alias and globals:
            globals[alias] = module
        return module


# ---------------------------------------------------------------------------
# Execution with timeout
# ---------------------------------------------------------------------------

_MAX_OUTPUT_CHARS: int = 50_000
_MAX_RESULT_STR_LEN: int = 20_000

# Semaphore limiting concurrent sandbox threads to prevent runaway growth.
_SANDBOX_CONCURRENCY_LIMIT: int = 5
_sandbox_semaphore: threading.Semaphore = threading.Semaphore(
    _SANDBOX_CONCURRENCY_LIMIT
)


def _target(
    code: str,
    global_ns: dict[str, Any],
    result_holder: list[Any],
) -> None:
    """Target function run in a separate thread."""
    try:
        exec(code, global_ns)
        # If the code assigns to `result`, capture it
        result_holder[0] = ("success", global_ns.get("result", None))
    except Exception:
        result_holder[0] = ("error", traceback.format_exc())


def run_code(
    code: str,
    timeout_seconds: int = 30,
    query_engine: QueryEngine | None = None,
) -> dict[str, Any]:
    """Execute *code* in a restricted sandbox and return the results.

    Parameters
    ----------
    code:
        Python source code to execute. May use ``result`` variable to
        pass a value back. ``print()`` output is captured.
    timeout_seconds:
        Maximum wall-clock time in seconds.  Default 30, max 120.
    query_engine:
        An optional ``QueryEngine`` instance to pass into the sandbox.
        If ``None``, the sandbox creates its own (which is the default).

    Returns
    -------
    dict with keys:
        - ``success``: ``bool``
        - ``stdout``: captured print output (``str``)
        - ``result``: value of ``result`` variable if set (``Any``)
        - ``error``: traceback string if an exception occurred (``str`` | ``None``)
        - ``truncated``: whether stdout was truncated (``bool``)
    """
    # Clamp timeout
    timeout_seconds = max(1, min(timeout_seconds, 120))

    # ── Build restricted global namespace ───────────────────────────────

    engine = query_engine or QueryEngine()

    builtins_copy: dict[str, Any] = dict(_SAFE_BUILTINS)
    builtins_copy["__import__"] = _RestrictedImporter(_ALLOWED_MODULES)

    global_ns: dict[str, Any] = {
        "__builtins__": builtins_copy,
        "__name__": "__sandbox__",
        # Provide data-access objects to the sandboxed code
        "engine": engine,
        # Pre-loaded Pydantic models for engine calls
        "SearchParams": SearchParams,
        "HighValueParams": HighValueParams,
        "SuspiciousPatternParams": SuspiciousPatternParams,
        "SummaryParams": SummaryParams,
        "SqlQueryParams": SqlQueryParams,
    }

    # Pre-import allowed modules that are available
    for mod_name in list(_ALLOWED_MODULES):
        try:
            module = __import__(mod_name)
            global_ns[mod_name] = module
            alias = _ALLOWED_MODULES[mod_name]
            if alias:
                global_ns[alias] = module
        except ImportError:
            pass

    # ── Enforce concurrency limit ───────────────────────────────────────

    acquired = _sandbox_semaphore.acquire(blocking=False)
    if not acquired:
        return {
            "success": False,
            "stdout": "",
            "result": None,
            "error": (
                f"Too many concurrent sandbox executions "
                f"(max {_SANDBOX_CONCURRENCY_LIMIT}). Try again later."
            ),
            "truncated": False,
        }

    thread: threading.Thread | None = None
    try:
        # ── Execute in a thread with timeout ────────────────────────────

        stdout_buf = io.StringIO()
        result_holder: list[Any] = [None]

        thread = threading.Thread(
            target=_target,
            args=(code, global_ns, result_holder),
            daemon=True,
        )

        with redirect_stdout(stdout_buf):
            thread.start()
            thread.join(timeout=timeout_seconds)

        # ── Collect output ─────────────────────────────────────────────

        stdout_text = stdout_buf.getvalue()
        truncated = len(stdout_text) > _MAX_OUTPUT_CHARS
        if truncated:
            stdout_text = stdout_text[:_MAX_OUTPUT_CHARS] + "\n... (truncated)"

        # ── Handle timeout ──────────────────────────────────────────────

        if thread.is_alive():
            # Thread still running – abandon it (daemon threads are cleaned
            # up on process exit). Semaphore NOT released – runaway thread
            # holds the slot so we don't accumulate more.
            return {
                "success": False,
                "stdout": stdout_text,
                "result": None,
                "error": (
                    f"Execution timed out after {timeout_seconds} seconds. "
                    f"Your code was automatically interrupted."
                ),
                "truncated": truncated,
            }

        # ── Handle result / error ───────────────────────────────────────

        status, payload = result_holder[0]

        if status == "error":
            return {
                "success": False,
                "stdout": stdout_text,
                "result": None,
                "error": payload,
                "truncated": truncated,
            }

        # Success – optionally truncate large result reprs
        result_val = payload
        if isinstance(result_val, str) and len(result_val) > _MAX_RESULT_STR_LEN:
            result_val = (
                result_val[:_MAX_RESULT_STR_LEN] + "\n... (result truncated)"
            )

        return {
            "success": True,
            "stdout": stdout_text,
            "result": result_val,
            "error": None,
            "truncated": truncated,
        }

    finally:
        # Release semaphore *unless* the thread timed out and is still
        # running – in that case the slot stays occupied.
        # Guard against the edge case where thread creation failed.
        if thread is not None and not thread.is_alive():
            _sandbox_semaphore.release()


__all__ = [
    "run_code",
    "_SAFE_BUILTINS",
    "_ALLOWED_MODULES",
]
