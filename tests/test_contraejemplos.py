"""Contraejemplos con valores concretos para las metas no demostradas (Ola 23)."""

import shutil

import pytest

from callahan.core.acsl import verificar_formal_frama_c
from callahan.core.contraejemplos import buscar_contraejemplo, ensures_del_contrato

con_wp = pytest.mark.skipif(not (shutil.which("frama-c") and (shutil.which("alt-ergo") or shutil.which("z3"))),
                            reason="requiere Frama-C y un prover")

ABSOLUTO = """/*@ assigns \\nothing;
    ensures \\result == n; */
int absol(int n) { return n < 0 ? -n : n; }
"""


def test_la_hipotesis_que_alcanza_y_el_ejemplo_confirmado():
    corridas = []

    def correr(texto):
        corridas.append(texto)
        if "callahan_testigo" in texto:
            return {"typed_absol_ensures", "typed_absol_ensures_callahan_vacio"}
        if "n >= 0" in texto:
            return {"typed_absol_ensures_callahan_vacio"}
        return {"typed_absol_ensures", "typed_absol_ensures_callahan_vacio"}

    ce = buscar_contraejemplo(ABSOLUTO, "absol", ["typed_absol_ensures"], correr)
    assert ce is not None and ce.hipotesis == "n >= 0" and ce.ejemplo == "-1"
    assert ("La función absol no asegura la postcondición si el parámetro n recibe un valor negativo "
            "(ej: n = -1).") in ce.mensaje
    assert "requires callahan_hipotesis: n == -1;" in corridas[-1]
    assert "ensures callahan_testigo: !((\\result == n));" in corridas[-1]


def test_una_hipotesis_que_contradice_al_contrato_se_descarta():
    # `ensures \false` demostrado: la hipótesis vuelve vacío al contrato y no explica nada.
    ce = buscar_contraejemplo(ABSOLUTO, "absol", ["typed_absol_ensures"], lambda texto: set())
    assert ce is None


def test_sin_confirmacion_no_hay_ejemplo():
    def correr(texto):
        if "callahan_testigo" in texto:
            return {"typed_absol_ensures_callahan_testigo", "typed_absol_ensures_callahan_vacio"}
        return {"typed_absol_ensures_callahan_vacio"}

    ce = buscar_contraejemplo(ABSOLUTO, "absol", ["typed_absol_ensures"], correr)
    assert ce is not None and ce.ejemplo is None and "(ej:" not in ce.mensaje


def test_los_behaviors_no_se_niegan():
    texto = "/*@ behavior a: assumes x > 0; ensures \\result == 1; */\nint f(int x) { return 1; }\n"
    assert ensures_del_contrato([texto], "f") is None
    assert ensures_del_contrato(["/*@ ensures pos: \\result >= 0;\n    ensures \\result < 10; */\nint g(int x);"], "g") \
        == ["\\result >= 0", "\\result < 10"]


@con_wp
def test_absoluto_con_frama_c(tmp_path):
    fuente = tmp_path / "absol.c"
    fuente.write_text(ABSOLUTO, encoding="utf-8")
    (c,) = verificar_formal_frama_c(fuente, timeout=3).contratos
    assert c.verificado_wp is False and c.contraejemplo is not None
    assert c.contraejemplo.mensaje.startswith(
        "La función absol no asegura la postcondición si el parámetro n recibe un valor negativo (ej: n = -1).")


@con_wp
def test_division_y_puntero_con_frama_c(tmp_path):
    fuente = tmp_path / "div.c"
    fuente.write_text("/*@ assigns \\nothing; ensures \\result == 100 / d; */\nint dividir(int d) { return 100 / d; }\n"
                      "/*@ assigns \\nothing; ensures \\result == *p; */\nint leer(int *p) { return *p; }\n",
                      encoding="utf-8")
    dividir, leer = verificar_formal_frama_c(fuente, timeout=3).contratos
    assert dividir.contraejemplo.hipotesis == "d != 0" and "puede dividir por cero" in dividir.contraejemplo.mensaje
    assert leer.contraejemplo.hipotesis == "\\valid(p)" and "no apunta a memoria válida" in leer.contraejemplo.mensaje


@con_wp
def test_sin_rte_un_desborde_pasa_y_con_rte_no(tmp_path):
    fuente = tmp_path / "doble.c"
    fuente.write_text("/*@ assigns \\nothing; ensures \\result == 2 * n; */\nint doble(int n) { return n + n; }\n",
                      encoding="utf-8")
    assert verificar_formal_frama_c(fuente, rte=False, timeout=3).ok is True
    rep = verificar_formal_frama_c(fuente, timeout=3, contraejemplos=False)
    assert rep.ok is False and any("_rte_signed_overflow" in m.meta for m in rep.metas)
