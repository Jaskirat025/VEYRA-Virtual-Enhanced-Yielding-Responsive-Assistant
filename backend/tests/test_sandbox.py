from __future__ import annotations

from backend.tools.sandbox import run_python


def test_runs_code_and_returns_stdout():
    result = run_python("print(6 * 7)")
    assert "exit_code=0" in result
    assert "42" in result


def test_network_module_is_blocked():
    result = run_python("import socket\nprint('reached')")
    assert "exit_code=1" in result
    assert "reached" not in result
    assert "disabled" in result.lower()


def test_timeout_is_reported():
    result = run_python("import time\ntime.sleep(5)", timeout=1)
    assert "timed out" in result.lower()


def test_output_is_truncated():
    result = run_python("print('x' * 5000)")
    assert len(result) < 2500
    assert "truncated" in result


def test_file_access_is_blocked():
    result = run_python("print(open('/etc/passwd').read())")
    assert "exit_code=1" in result
    assert "disabled" in result.lower()
    assert "root:" not in result


def test_private_attributes_are_blocked():
    result = run_python("print((1).__class__.__mro__)")
    assert "exit_code=1" in result
    assert "private attributes" in result.lower()
