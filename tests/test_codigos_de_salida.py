"""Regresión de CALLAHAN-D0403: `verify` mezclaba "no se pudo verificar" con "se verificó y falló".

Sin Frama-C (prover opcional) salía con 1, el mismo código de un contrato rechazado, y un
consumidor automatizado no podía distinguir una dependencia ausente de una regresión real.
Contrato: 0 verificado, 1 contrato rechazado, 2 no se pudo verificar.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import callahan.cli as cli_mod
from callahan.cli import app
from callahan.core.models import ContratoACSL, ReporteVerificacion

runner = CliRunner()

CON_CONTRATO = "/*@ requires x >= 0; */ int f(int x) { return x; }\n"
SIN_CONTRATO = "int f(int x) { return x; }\n"


def _reporte(archivo: Path, *, frama: bool, verificado: bool | None, contratos: bool = True):
    lista = [ContratoACSL(funcion="f", archivo=archivo, linea_inicio=1, verificado_wp=bool(verificado))] if contratos else []
    return ReporteVerificacion(archivo=archivo, contratos=lista, frama_c_disponible=frama)


@pytest.fixture
def fuente(tmp_path):
    ruta = tmp_path / "c.c"
    ruta.write_text(CON_CONTRATO, encoding="utf-8")
    return ruta


@pytest.mark.parametrize(
    "frama, verificado, contratos, esperado",
    [
        (True, True, True, 0),     # se probó todo
        (True, False, True, 1),    # Frama-C rechazó un contrato: regresión real
        (False, False, True, 2),   # no se pudo verificar
        (False, False, False, 0),  # sin contratos no hay nada que verificar
        (True, False, False, 0),
    ],
)
@pytest.mark.parametrize("modo", ["rich", "json", "md"])
def test_el_codigo_de_salida_distingue_los_tres_casos_en_todos_los_modos(
    monkeypatch, fuente, tmp_path, modo, frama, verificado, contratos, esperado
):
    monkeypatch.setattr(cli_mod, "verificar_formal_frama_c", lambda f: _reporte(f, frama=frama, verificado=verificado, contratos=contratos))
    args = ["verify", str(fuente)]
    if modo == "json":
        args.append("--json")
    elif modo == "md":
        args += ["--md", str(tmp_path / "r.md")]
    assert runner.invoke(app, args).exit_code == esperado


def test_sin_frama_c_real_los_contratos_no_verificados_salen_con_2(fuente):
    import shutil

    if shutil.which("frama-c"):
        pytest.skip("con Frama-C instalado el resultado depende del prover")
    assert runner.invoke(app, ["verify", str(fuente)]).exit_code == 2


def test_un_archivo_sin_contratos_es_ok_con_o_sin_frama_c(tmp_path):
    ruta = tmp_path / "s.c"
    ruta.write_text(SIN_CONTRATO, encoding="utf-8")
    res = runner.invoke(app, ["verify", str(ruta), "--json"])
    assert res.exit_code == 0
    assert json.loads(res.output)["ok"] is True


def test_el_json_sigue_distinguiendo_la_causa_por_campos(monkeypatch, fuente):
    monkeypatch.setattr(cli_mod, "verificar_formal_frama_c", lambda f: _reporte(f, frama=False, verificado=False))
    datos = json.loads(runner.invoke(app, ["verify", str(fuente), "--json"]).output)
    assert datos["frama_c_disponible"] is False and datos["ok"] is False
