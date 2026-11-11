"""Sandboxed Python execution for the ``esegui_python`` tool.

The child process runs isolated (``-I``), in a temporary directory, with a
stripped environment and a wall-clock timeout. Model-generated code is checked
before it runs: only a small set of pure-standard-library imports is accepted,
dunder attributes are rejected, and the execution namespace has no file,
process, network or introspection helpers. This is a pragmatic sandbox, not a
claim of perfect isolation against a determined attacker; it is deliberately
closed by default so ordinary snippets cannot touch user files or the network.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:  # POSIX only; Windows uses the timeout alone.
    import resource
except ImportError:  # pragma: no cover - Windows
    resource = None  # type: ignore[assignment]

RUNNER = """\
import ast
import builtins
import sys

ALLOWED_IMPORTS = {
    "collections", "datetime", "decimal", "fractions", "functools",
    "itertools", "json", "math", "random", "re", "statistics", "string",
    "textwrap", "time", "typing", "unicodedata",
}
BLOCKED_NAMES = {
    "__builtins__", "__import__", "open", "eval", "exec", "compile",
    "input", "getattr", "setattr", "delattr", "globals", "locals", "vars",
    "breakpoint", "help", "exit", "quit",
}


class _Validator(ast.NodeVisitor):
    def _check_module(self, name):
        root = name.split(".")[0]
        if root not in ALLOWED_IMPORTS:
            raise SyntaxError("This import is disabled inside the Veyra sandbox: " + name)

    def visit_Import(self, node):
        for alias in node.names:
            self._check_module(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.level:
            raise SyntaxError("Relative imports are disabled inside the Veyra sandbox.")
        self._check_module(node.module or "")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in BLOCKED_NAMES:
            raise SyntaxError("This name is disabled inside the Veyra sandbox: " + node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr.startswith("__"):
            raise SyntaxError("Private attributes are disabled inside the Veyra sandbox.")
        self.generic_visit(node)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level:
        raise ImportError("Relative imports are disabled inside the Veyra sandbox.")
    if name.split(".")[0] not in ALLOWED_IMPORTS:
        raise ImportError("This module is disabled inside the Veyra sandbox: " + name)
    return __import__(name, globals, locals, fromlist, 0)


safe_builtins = {
    name: value
    for name, value in vars(builtins).items()
    if name not in BLOCKED_NAMES and not name.startswith("__")
}
safe_builtins["__build_class__"] = builtins.__build_class__
safe_builtins["__import__"] = _safe_import

target = sys.argv[1]
with open(target, encoding="utf-8") as handle:
    source = handle.read()

try:
    tree = ast.parse(source, filename="sandbox.py")
    _Validator().visit(tree)
except SyntaxError as error:
    print("Sandbox error: " + str(error))
    raise SystemExit(1) from None

sys.argv = ["sandbox"]
exec(compile(tree, "sandbox.py", "exec"), {"__name__": "__main__", "__builtins__": safe_builtins})
"""


def run_python(code: str, timeout: int = 20) -> str:
    """Execute ``code`` and return combined output, or a readable error."""
    with tempfile.TemporaryDirectory(prefix="veyra-sandbox-") as workdir:
        directory = Path(workdir)
        script = directory / "sandbox.py"
        runner = directory / "runner.py"
        script.write_text(code, encoding="utf-8")
        runner.write_text(RUNNER, encoding="utf-8")

        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "TEMP": str(directory),
            "TMP": str(directory),
            "MPLBACKEND": "Agg",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONHASHSEED": "0",
        }

        def limit_resources() -> None:  # pragma: no cover - POSIX only
            if resource is None:
                return
            try:
                resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024,) * 2)
                resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 2))
            except (ValueError, OSError):
                pass

        try:
            completed = subprocess.run(
                [sys.executable, "-I", str(runner), str(script)],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=limit_resources if os.name != "nt" else None,
            )
        except subprocess.TimeoutExpired:
            return f"Execution timed out after {timeout} seconds."

        output = (completed.stdout or "") + (completed.stderr or "")
        output = output.strip()
        if not output:
            output = "(no output)"
        if len(output) > 1900:
            output = output[:1900] + "\n...[truncated]"
        return f"exit_code={completed.returncode}\n{output}"
