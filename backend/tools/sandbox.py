"""Sandboxed Python execution for the ``esegui_python`` tool.

The child process runs isolated (``-I``), in a temporary directory, with a
stripped environment, a wall-clock timeout and a best-effort import/network
block list. This is a pragmatic sandbox, not a security boundary against a
determined attacker; it exists so a model-generated snippet cannot casually
read user files or reach the network.
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
import sys

BLOCKED = {
    "ctypes", "ftplib", "http", "multiprocessing", "requests", "smtplib",
    "socket", "subprocess", "telnetlib", "urllib", "winreg",
}


class _Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCKED:
            raise ImportError(
                "This module is disabled inside the Veyra sandbox: " + fullname
            )
        return None


sys.meta_path.insert(0, _Blocker())

target = sys.argv[1]
with open(target, encoding="utf-8") as handle:
    source = handle.read()
sys.argv = ["sandbox"]
exec(compile(source, "sandbox.py", "exec"), {"__name__": "__main__"})
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
