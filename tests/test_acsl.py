"""Tests unitarios para el analizador de contratos ACSL en CALLAHAN."""

from pathlib import Path
import pytest
from callahan.core.acsl import extraer_contratos_acsl, verificar_formal_frama_c


def test_extraer_contrato_acsl(tmp_path):
    fuente = tmp_path / "suma.c"
    fuente.write_text("""
    /*@
      @ requires a >= 0 && b >= 0;
      @ ensures \\result >= 0;
      @ assigns \\nothing;
    */
    int sumar(int a, int b) {
        return a + b;
    }
    """)

    contratos = extraer_contratos_acsl(fuente)
    assert len(contratos) == 1
    c = contratos[0]
    assert c.funcion == "sumar"
    assert len(c.clausulas) == 3
    tipos = [cl.tipo for cl in c.clausulas]
    assert "requires" in tipos
    assert "ensures" in tipos
    assert "assigns" in tipos


def test_verificar_formal_fallback(tmp_path):
    fuente = tmp_path / "suma.c"
    fuente.write_text("""
    /*@ requires x > 0; ensures \\result == x * 2; */
    int doble(int x) { return x * 2; }
    """)

    rep = verificar_formal_frama_c(fuente)
    assert rep.ok is True
    assert len(rep.contratos) == 1
