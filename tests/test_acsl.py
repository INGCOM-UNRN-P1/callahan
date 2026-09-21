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


def test_verificar_formal_fallback(tmp_path, sin_frama_c):
    fuente = tmp_path / "suma.c"
    fuente.write_text("""
    /*@ requires x > 0; ensures \\result == x * 2; */
    int doble(int x) { return x * 2; }
    """)

    rep = verificar_formal_frama_c(fuente)
    assert rep.frama_c_disponible is False
    assert rep.ok is False
    assert len(rep.contratos) == 1
    assert rep.contratos[0].verificado_wp is False
    assert "UNVERIFIED" in rep.contratos[0].mensaje_prover


def test_verificar_formal_frama_c_mock(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda t, *a, **k: "/usr/bin/" + t if t in ("frama-c", "alt-ergo") else None)
    class MockRes:
        stdout = "Proved goals: 100%"
        returncode = 0
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: MockRes())

    fuente = tmp_path / "suma.c"
    fuente.write_text("""
    /*@ requires x > 0; ensures \\result == x * 2; */
    int doble(int x) { return x * 2; }
    """)

    rep = verificar_formal_frama_c(fuente)
    assert rep.frama_c_disponible is True
    assert rep.ok is True
    assert rep.contratos[0].verificado_wp is True


def test_sin_ningun_prover_instalado_es_no_verificable(monkeypatch, tmp_path):
    """Frama-C presente pero sin alt-ergo ni z3: 'no se pudo verificar', no 'contrato rechazado'."""
    real = __import__("shutil").which
    monkeypatch.setattr("shutil.which", lambda t, *a, **k: "/usr/bin/frama-c" if t == "frama-c" else (None if t in ("alt-ergo", "z3") else real(t, *a, **k)))
    fuente = tmp_path / "f.c"
    fuente.write_text("/*@ requires x > 0; */ int f(int x) { return x; }\n")
    rep = verificar_formal_frama_c(fuente)
    assert rep.frama_c_disponible is False
    assert rep.codigo_de_salida == 2
    assert "ningún prover" in rep.contratos[0].mensaje_prover


def test_solo_se_le_pasan_a_frama_c_los_provers_instalados(monkeypatch, tmp_path):
    real = __import__("shutil").which
    monkeypatch.setattr("shutil.which", lambda t, *a, **k: "/usr/bin/" + t if t in ("frama-c", "alt-ergo") else (None if t == "z3" else real(t, *a, **k)))
    capturado = {}

    class R:
        stdout, returncode = "Proved goals: 100%", 0

    monkeypatch.setattr("subprocess.run", lambda cmd, **k: capturado.setdefault("cmd", cmd) and R())
    fuente = tmp_path / "f.c"
    fuente.write_text("/*@ requires x > 0; */ int f(int x) { return x; }\n")
    verificar_formal_frama_c(fuente)
    assert capturado["cmd"][capturado["cmd"].index("-wp-prover") + 1] == "alt-ergo"
