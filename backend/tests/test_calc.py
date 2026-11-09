from __future__ import annotations

import pytest

pytest.importorskip("sympy")

from backend.tools.builtin.calc import calcola, converti_unita, risolvi_equazione
from backend.tools.registry import ToolError


def test_calcola_returns_exact_and_decimal():
    assert calcola("245 * 0.17") == "41.65"
    assert calcola("12 * 8") == "96"
    assert "0.7071" in calcola("sqrt(2)/2")


def test_calcola_rejects_variables_and_code():
    with pytest.raises(ToolError):
        calcola("x + 1")
    with pytest.raises(ToolError):
        calcola("__import__('os')")


def test_unit_conversion_length_and_temperature():
    assert "0.621371" in converti_unita(1, "km", "mi")
    assert "1.60934" in converti_unita(1, "mi", "km")
    assert converti_unita(0, "c", "f") == "32.00 f"
    with pytest.raises(ToolError):
        converti_unita(1, "km", "c")


def test_equation_solver():
    assert "9" in risolvi_equazione("2*x - 18 = 0")
    with pytest.raises(ToolError):
        risolvi_equazione("this is not math")
