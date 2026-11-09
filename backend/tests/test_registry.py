from __future__ import annotations

import pytest
from backend.tools.registry import (
    Risk,
    ToolError,
    ensure_tools_loaded,
    get_tool,
    validate_arguments,
)

EXPECTED_TOOLS = {
    "apri_app",
    "chiudi_app",
    "volume",
    "luminosita",
    "screenshot",
    "stato_pc",
    "appunti",
    "finestre",
    "clicca",
    "scrivi",
    "scorciatoia",
    "cerca_file",
    "leggi_file",
    "sposta_file",
    "elimina_file",
    "calcola",
    "converti_unita",
    "risolvi_equazione",
    "grafico",
    "esegui_python",
    "lista_repo",
    "leggi_issue",
    "ultimi_commit",
    "crea_issue",
    "cerca_mail",
    "leggi_mail",
    "bozza_mail",
    "invia_mail",
    "eventi_oggi",
    "eventi_range",
    "crea_evento",
    "salva_nota",
    "cerca_note",
    "timer",
    "sveglia",
    "chiedi_chiarimento",
}


def test_all_expected_tools_are_registered():
    registry = ensure_tools_loaded()
    assert EXPECTED_TOOLS.issubset(set(registry))


def test_schema_uses_type_hints_and_docstring():
    spec = get_tool("calcola")
    assert spec is not None
    assert spec.parameters["required"] == ["espressione"]
    assert spec.parameters["properties"]["espressione"]["type"] == "string"
    assert "Example" in spec.description or "expression" in spec.description
    assert spec.risk is Risk.SAFE


def test_risk_levels_are_declared():
    assert get_tool("elimina_file").risk is Risk.DANGEROUS
    assert get_tool("chiudi_app").risk is Risk.CONFIRM
    assert get_tool("invia_mail").risk is Risk.CONFIRM
    assert get_tool("esegui_python").risk is Risk.DANGEROUS


def test_validation_rejects_unknown_and_missing_arguments():
    spec = get_tool("calcola")
    with pytest.raises(ToolError):
        validate_arguments(spec, {"espressione": "1+1", "extra": True})
    with pytest.raises(ToolError):
        validate_arguments(spec, {})


def test_validation_rejects_wrong_types_and_oversized_strings():
    spec = get_tool("calcola")
    with pytest.raises(ToolError):
        validate_arguments(spec, {"espressione": 42})
    with pytest.raises(ToolError):
        validate_arguments(spec, {"espressione": "1" * 5000})


def test_enum_arguments_are_enforced():
    spec = get_tool("volume")
    assert validate_arguments(spec, {"azione": "su", "valore": 5})["azione"] == "su"
    with pytest.raises(ToolError):
        validate_arguments(spec, {"azione": "explode"})
