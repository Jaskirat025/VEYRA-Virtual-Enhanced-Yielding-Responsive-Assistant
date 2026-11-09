"""Calculation tools. The model must never compute arithmetic itself."""

from __future__ import annotations

import uuid

from backend.paths import charts_dir
from backend.tools.registry import Category, Risk, ToolError, tool

_ALLOWED_CHARS = set("0123456789+-*/().,^ %=abcdefghijklmnopqrstuvwxyz_")


def _sympy():
    try:
        import sympy
        from sympy.parsing.sympy_parser import (
            convert_xor,
            implicit_multiplication_application,
            parse_expr,
            standard_transformations,
        )
    except ImportError as exc:
        raise ToolError("SymPy is not installed.") from exc
    return (
        sympy,
        parse_expr,
        standard_transformations,
        (
            implicit_multiplication_application,
            convert_xor,
        ),
    )


def _clean_expression(expression: str, *, allow_equals: bool = False) -> str:
    text = expression.strip()
    if not text:
        raise ToolError("The expression is empty.")
    if len(text) > 300:
        raise ToolError("The expression is too long.")
    if not allow_equals and "=" in text:
        raise ToolError("Use risolvi_equazione for equations.")
    if any(character.lower() not in _ALLOWED_CHARS for character in text):
        raise ToolError("The expression contains unsupported characters.")
    return text


@tool(category=Category.CALC, risk=Risk.SAFE)
def calcola(espressione: str) -> str:
    """Evaluate a mathematical expression exactly.

    Use for every arithmetic request, including percentages and unit-free math.
    Never compute in your head.

    Args:
        espressione: expression such as "245 * 0.17" or "sqrt(2)/2".
    """
    sympy, parse_expr, transformations, extra = _sympy()
    text = _clean_expression(espressione)
    local_dict = {
        "sqrt": sympy.sqrt,
        "sin": sympy.sin,
        "cos": sympy.cos,
        "tan": sympy.tan,
        "log": sympy.log,
        "ln": sympy.log,
        "exp": sympy.exp,
        "pi": sympy.pi,
        "abs": sympy.Abs,
        "factorial": sympy.factorial,
    }
    try:
        expression = parse_expr(
            text,
            local_dict=local_dict,
            transformations=transformations + extra,
            evaluate=True,
        )
    except Exception as exc:
        raise ToolError(f"Could not parse the expression: {exc}") from exc

    if expression.free_symbols:
        raise ToolError("The expression contains unknown variables.")
    try:
        simplified = sympy.simplify(expression)
        value = float(simplified)
    except (TypeError, ValueError) as exc:
        raise ToolError(f"Could not evaluate the expression: {exc}") from exc

    if isinstance(simplified, sympy.Integer):
        return str(int(simplified))
    if isinstance(simplified, sympy.Rational):
        return f"{float(simplified):.10g}"
    if isinstance(simplified, sympy.Float):
        return f"{value:.10g}"
    return f"{simplified} (≈ {value:.10g})"


_LENGTH = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1000.0,
    "in": 0.0254,
    "ft": 0.3048,
    "yd": 0.9144,
    "mi": 1609.344,
}
_MASS = {"mg": 1e-6, "g": 0.001, "kg": 1.0, "t": 1000.0, "oz": 0.0283495, "lb": 0.453592}
_VOLUME = {"ml": 0.001, "l": 1.0, "m3": 1000.0, "cup": 0.236588, "qt": 0.946353, "gal": 3.78541}
_DATA = {
    "b": 1.0,
    "kb": 1000.0,
    "mb": 1000.0**2,
    "gb": 1000.0**3,
    "tb": 1000.0**4,
    "kib": 1024.0,
    "mib": 1024.0**2,
    "gib": 1024.0**3,
    "tib": 1024.0**4,
}
_SPEED = {"m/s": 1.0, "km/h": 0.277778, "mph": 0.44704, "kn": 0.514444}
_TIME = {"s": 1.0, "min": 60.0, "h": 3600.0, "d": 86400.0}

_UNIT_TABLES = {
    "length": _LENGTH,
    "mass": _MASS,
    "volume": _VOLUME,
    "data": _DATA,
    "speed": _SPEED,
    "time": _TIME,
}
_ALIASES = {
    "metri": "m",
    "metro": "m",
    "meters": "m",
    "meter": "m",
    "chilometri": "km",
    "kilometers": "km",
    "centimetri": "cm",
    "millimetri": "mm",
    "grammi": "g",
    "kilograms": "kg",
    "chilogrammi": "kg",
    "litri": "l",
    "liters": "l",
    "milliliters": "ml",
    "celsius": "c",
    "fahrenheit": "f",
    "kelvin": "k",
    "secondi": "s",
    "minuti": "min",
    "ore": "h",
    "giorni": "d",
    "gigabytes": "gb",
    "megabytes": "mb",
}


@tool(category=Category.CALC, risk=Risk.SAFE)
def converti_unita(valore: float, da: str, a: str) -> str:
    """Convert a value between compatible units.

    Use for length, mass, volume, data size, speed, time and temperature.

    Args:
        valore: numeric value to convert.
        da: source unit, for example "km" or "celsius".
        a: target unit, for example "mi" or "fahrenheit".
    """
    source = _ALIASES.get(da.strip().lower(), da.strip().lower())
    target = _ALIASES.get(a.strip().lower(), a.strip().lower())

    temperature = {"c", "f", "k"}
    if source in temperature or target in temperature:
        if source not in temperature or target not in temperature:
            raise ToolError("Temperature units cannot be mixed with other units.")
        celsius = {"c": valore, "f": (valore - 32) * 5 / 9, "k": valore - 273.15}[source]
        result = {"c": celsius, "f": celsius * 9 / 5 + 32, "k": celsius + 273.15}[target]
        return f"{result:.2f} {target}"

    for table in _UNIT_TABLES.values():
        if source in table and target in table:
            result = valore * table[source] / table[target]
            return f"{result:.6g} {target}"

    raise ToolError(f"Cannot convert from '{da}' to '{a}'.")


@tool(category=Category.CALC, risk=Risk.SAFE)
def risolvi_equazione(equazione: str, variabile: str = "x") -> str:
    """Solve an equation for one variable.

    Use when the user asks to solve an equation, linear or not.

    Args:
        equazione: equation text such as "2*x + 3 = 11".
        variabile: variable to solve for, default "x".
    """
    sympy, parse_expr, transformations, extra = _sympy()
    text = _clean_expression(equazione, allow_equals=True)
    name = (variabile or "x").strip()
    if not name.isidentifier():
        raise ToolError("The variable name is invalid.")
    symbol = sympy.Symbol(name)

    try:
        if "=" in text:
            left, right = text.split("=", 1)
            equation = sympy.Eq(
                parse_expr(
                    left, local_dict={name: symbol}, transformations=transformations + extra
                ),
                parse_expr(
                    right, local_dict={name: symbol}, transformations=transformations + extra
                ),
            )
        else:
            equation = sympy.Eq(
                parse_expr(
                    text, local_dict={name: symbol}, transformations=transformations + extra
                ),
                0,
            )
        solutions = sympy.solve(equation, symbol)
    except Exception as exc:
        raise ToolError(f"Could not solve the equation: {exc}") from exc

    if not solutions:
        return "No solution found."
    return f"{name} = " + ", ".join(str(solution) for solution in solutions)


@tool(category=Category.CALC, risk=Risk.SAFE)
def grafico(
    espressione: str, variabile: str = "x", minimo: float = -10, massimo: float = 10
) -> str:
    """Plot a function and save it as a PNG chart.

    Use when the user asks to see a graph or plot.

    Args:
        espressione: function of the variable, such as "sin(x) + x/3".
        variabile: variable name, default "x".
        minimo: left bound of the x axis.
        massimo: right bound of the x axis.
    """
    sympy, parse_expr, transformations, extra = _sympy()
    text = _clean_expression(espressione)
    name = (variabile or "x").strip()
    if not name.isidentifier():
        raise ToolError("The variable name is invalid.")
    if massimo <= minimo:
        raise ToolError("The maximum must be greater than the minimum.")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        symbol = sympy.Symbol(name)
        expression = parse_expr(
            text,
            local_dict={name: symbol},
            transformations=transformations + extra,
        )
        function = sympy.lambdify(symbol, expression, modules=["numpy"])
        x_values = np.linspace(minimo, massimo, 800)
        y_values = function(x_values)
        if np.isscalar(y_values):
            y_values = np.full_like(x_values, float(y_values))

        figure, axes = plt.subplots(figsize=(7, 4), dpi=110)
        axes.plot(x_values, np.asarray(y_values, dtype=float), color="#ff5a1f", linewidth=1.6)
        axes.grid(True, color="#c5cbd055", linewidth=0.6)
        axes.set_facecolor("#1e262a")
        figure.patch.set_facecolor("#161c1f")
        axes.tick_params(colors="#c5cbd0")
        for spine in axes.spines.values():
            spine.set_color("#3a464c")
        destination = charts_dir() / f"chart-{uuid.uuid4().hex[:8]}.png"
        figure.tight_layout()
        figure.savefig(destination, facecolor=figure.get_facecolor())
        plt.close(figure)
    except Exception as exc:
        raise ToolError(f"Could not create the chart: {exc}") from exc

    return f"Chart saved to {destination}."
