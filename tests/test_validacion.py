"""Validación de las anotaciones ACSL antes de los provers (Ola 23)."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from callahan.cli import app
from callahan.core.validacion import analizar_salida_kernel

runner = CliRunner()
con_frama_c = pytest.mark.skipif(not shutil.which("frama-c"), reason="requiere Frama-C")

SALIDA = """[kernel] Parsing errs.c (with preprocessing)
[kernel:annot-error] errs.c:3: Warning:
  unbound logic variable m. Ignoring logic specification of function b
[kernel:annot-error] errs.c:6: Warning: expecting ';' before ensures
[kernel:annot-error] errs.c:20: Warning:
  Assignment operators not allowed in annotations.
"""


def test_traduce_todos_los_errores_con_su_linea():
    errores = analizar_salida_kernel(SALIDA)
    assert [(e.archivo, e.linea) for e in errores] == [("errs.c", 3), ("errs.c", 6), ("errs.c", 20)]
    assert "`m` no está declarada" in errores[0].explicacion
    assert "ignora el contrato entero de b" in errores[0].explicacion
    assert "Falta `;` antes de `ensures`" in errores[1].explicacion
    assert "usá `==`" in errores[2].explicacion


def test_un_error_de_sintaxis_de_c_se_deriva_a_daedalus():
    salida = ('[kernel] csyn.c:1: \n  syntax error:\n  Location: "csyn.c", line 1, before or at token: {\n'
              "[kernel] Frama-C aborted: invalid user input.\n")
    (error,) = analizar_salida_kernel(salida)
    assert error.tipo == "c" and error.linea == 1 and "daedalus compile" in error.explicacion


def test_un_mensaje_desconocido_se_muestra_tal_cual():
    (error,) = analizar_salida_kernel("[kernel:annot-error] a.c:2: Warning: algo nuevo\n")
    assert error.explicacion == "Frama-C no entiende esta anotación: algo nuevo"


@con_frama_c
def test_check_lista_todos_los_errores_y_sale_con_1(tmp_path):
    fuente = tmp_path / "mal.c"
    fuente.write_text("/*@ requires y > 0; */\nint inc(int x) { return x + 1; }\n"
                      "/*@ requires n >= 0\n    ensures \\result >= 0; */\nint f(int n) { return n; }\n",
                      encoding="utf-8")
    res = runner.invoke(app, ["check", str(fuente), "--json"])
    assert res.exit_code == 1
    datos = json.loads(res.output)
    assert sorted(e["linea"] for e in datos["errores"]) == [1, 3]
    assert all(e["archivo"] == str(fuente) for e in datos["errores"])


@con_frama_c
def test_verify_no_llama_a_los_provers_si_el_contrato_esta_mal(tmp_path):
    fuente = tmp_path / "mal.c"
    fuente.write_text("/*@ ensures \\result == m; */\nint f(int n) { return n; }\n", encoding="utf-8")
    res = runner.invoke(app, ["verify", str(fuente), "--json"])
    assert res.exit_code == 1
    datos = json.loads(res.output)
    assert datos["ok"] is False and datos["metas_no_demostradas"] == []
    assert "`m` no está declarada" in datos["errores_acsl"][0]["explicacion"]


@con_frama_c
def test_check_de_un_archivo_correcto(tmp_path):
    fuente = tmp_path / "ok.c"
    fuente.write_text("/*@ requires n >= 0; ensures \\result == n; */\nint f(int n) { return n; }\n", encoding="utf-8")
    assert runner.invoke(app, ["check", str(fuente)]).exit_code == 0
