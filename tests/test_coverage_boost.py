"""Tests adicionales para maximizar la cobertura en CALLAHAN."""

import json
from pathlib import Path
from typer.testing import CliRunner
import callahan.cli
from callahan.cli import app
from callahan.core.acsl import extraer_contratos_acsl, verificar_formal_frama_c
from callahan.ripley_plugin import CallahanPlugin

runner = CliRunner()


def test_plugin_execution(tmp_path):
    p = CallahanPlugin()
    assert p.is_available() is True

    f = tmp_path / "suma.c"
    f.write_text("/*@ requires a > 0; ensures \\result > 0; */ int f(int a) { return a; }\n")
    res = p.execute(tmp_path, {})
    assert res["ok"] is False
    assert res["total_contratos"] == 1
    assert len(res["observaciones"]) == 1
    assert res["observaciones"][0]["codigo"] == "FORMAL_WP_UNVERIFIED"


def test_cli_verify_rich_and_empty(tmp_path):
    # With contracts (sin frama-c -> UNVERIFIED -> exit code 1)
    f = tmp_path / "code.c"
    f.write_text("/*@ requires x >= 0; */ int f(int x) { return x; }\n")
    res = runner.invoke(app, ["verify", str(f)])
    assert res.exit_code == 1
    assert "Contratos ACSL Detectados" in res.stdout
    assert "UNVERIFIED" in res.stdout

    # Without contracts
    f_empty = tmp_path / "no_acsl.c"
    f_empty.write_text("int f(int x) { return x; }\n")
    res_empty = runner.invoke(app, ["verify", str(f_empty)])
    assert res_empty.exit_code == 0
    assert "No se encontraron contratos" in res_empty.stdout


def test_cli_extract_rich(tmp_path):
    f = tmp_path / "code.c"
    f.write_text("/*@ requires x > 0; ensures \\result > 0; */ int f(int x) { return x; }\n")
    res = runner.invoke(app, ["extract", str(f)])
    assert res.exit_code == 0
    assert "Contrato para f()" in res.stdout


def test_cli_file_not_found():
    res = runner.invoke(app, ["verify", "/no/existe.c"])
    assert res.exit_code == 2


def test_cli_main_block(monkeypatch):
    monkeypatch.setattr("sys.argv", ["callahan", "--version"])
    try:
        callahan.cli.main()
    except SystemExit as e:
        assert e.code == 0
