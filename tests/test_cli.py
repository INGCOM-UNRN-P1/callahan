"""Tests de integración de la CLI de CALLAHAN."""

import json
from pathlib import Path
from typer.testing import CliRunner
from callahan.cli import app

runner = CliRunner()


def test_cli_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "CALLAHAN" in res.stdout


def test_cli_doctor():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "frama-c" in res.stdout


def test_cli_extract_json(tmp_path):
    fuente = tmp_path / "code.c"
    fuente.write_text("/*@ requires n > 0; */ int f(int n) { return n; }\n")

    res = runner.invoke(app, ["extract", str(fuente), "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert len(data) == 1
    assert data[0]["funcion"] == "f"
