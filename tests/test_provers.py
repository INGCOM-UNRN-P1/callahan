"""Canario de provers: uno que demuestra metas falsas no se usa (Z3 4.16 con Frama-C 33)."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from callahan.cli import app
from callahan.core import provers
from callahan.core.acsl import verificar_formal_frama_c

runner = CliRunner()
FUENTE = "/*@ assigns \\nothing; ensures \\result == n; */\nint f(int n) { return n; }\n"


class _Res:
    def __init__(self, stdout):
        self.stdout, self.stderr, self.returncode = stdout, "", 0


@pytest.fixture
def instalados(monkeypatch, tmp_path):
    """frama-c, alt-ergo y z3 «instalados» como archivos reales (la huella los necesita)."""
    rutas = {}
    for nombre in ("frama-c", "alt-ergo", "z3"):
        rutas[nombre] = tmp_path / "bin" / nombre
        rutas[nombre].parent.mkdir(exist_ok=True)
        rutas[nombre].write_text("#!/bin/sh\n")
    monkeypatch.setattr("shutil.which", lambda t, *a, **k: str(rutas[t]) if t in rutas else None)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return rutas


def _canario_falla_con(monkeypatch, inconsistentes, llamadas=None):
    def correr(cmd, **k):
        if "callahan_canario" in cmd:
            if llamadas is not None:
                llamadas.append(cmd[cmd.index("-wp-prover") + 1])
            prover = cmd[cmd.index("-wp-prover") + 1]
            return _Res("Proved goals:    3 / 3" if prover in inconsistentes else "Proved goals:    2 / 3")
        if "--version" in cmd:
            return _Res("Z3 version 4.16.0 - 64 bit")
        return _Res("[wp] Proved goals:    4 / 4")
    monkeypatch.setattr("subprocess.run", correr)


def test_el_prover_que_demuestra_el_canario_se_descarta(monkeypatch, instalados):
    _canario_falla_con(monkeypatch, {"z3"})
    confiables, descartados = provers.separar_provers(str(instalados["frama-c"]), ["alt-ergo", "z3"])
    assert confiables == ["alt-ergo"] and descartados == ["z3"]


def test_el_resultado_queda_en_cache_hasta_que_cambia_el_prover(monkeypatch, instalados):
    llamadas = []
    _canario_falla_con(monkeypatch, {"z3"}, llamadas)
    frama_c = str(instalados["frama-c"])
    assert provers.prover_confiable(frama_c, "z3") is False
    assert provers.prover_confiable(frama_c, "z3") is False
    assert llamadas == ["z3"]
    instalados["z3"].write_text("#!/bin/sh\n# z3 actualizado\n")
    assert provers.prover_confiable(frama_c, "z3") is False
    assert llamadas == ["z3", "z3"]


def test_si_frama_c_no_responde_el_prover_se_da_por_confiable_sin_guardarlo(monkeypatch, instalados):
    monkeypatch.setattr("subprocess.run", lambda cmd, **k: _Res("[kernel] user error"))
    assert provers.prover_confiable(str(instalados["frama-c"]), "z3") is True
    assert not provers._archivo_cache().exists()


def test_verify_no_usa_el_prover_descartado(monkeypatch, instalados, tmp_path):
    comandos = []
    _canario_falla_con(monkeypatch, {"z3"})
    original = __import__("subprocess").run
    monkeypatch.setattr("subprocess.run", lambda cmd, **k: comandos.append(cmd) or original(cmd, **k))
    fuente = tmp_path / "f.c"
    fuente.write_text(FUENTE)
    rep = verificar_formal_frama_c(fuente)
    wp = next(c for c in comandos if "-wp-rte" in c)
    assert wp[wp.index("-wp-prover") + 1] == "alt-ergo"
    assert rep.provers_descartados == ["z3"]
    assert rep.to_dict()["provers_descartados"] == ["z3"]


def test_sin_provers_confiables_no_se_puede_verificar(monkeypatch, instalados, tmp_path):
    _canario_falla_con(monkeypatch, {"z3", "alt-ergo"})
    fuente = tmp_path / "f.c"
    fuente.write_text(FUENTE)
    res = runner.invoke(app, ["verify", str(fuente), "--json"])
    assert res.exit_code == 2  # no se pudo verificar, no «contrato rechazado» ni «probado»
    datos = json.loads(res.stdout)
    assert datos["ok"] is False and set(datos["provers_descartados"]) == {"z3", "alt-ergo"}
    assert "ningún prover confiable" in datos["contratos"][0]["mensaje_prover"]


def test_doctor_avisa_del_prover_descartado(monkeypatch, instalados):
    _canario_falla_con(monkeypatch, {"z3"})
    res = runner.invoke(app, ["doctor", "--json"])
    assert res.exit_code == 0  # frama-c está: el aviso es de un opcional
    chequeo = next(c for c in json.loads(res.stdout)["chequeos"] if c["nombre"].startswith("z3 ("))
    assert chequeo["ok"] is False and "Z3 4.16.0 demuestra metas falsas" in chequeo["detalle"]


@pytest.mark.skipif(not shutil.which("frama-c"), reason="requiere Frama-C")
@pytest.mark.parametrize("prover", [p for p in ("alt-ergo", "z3") if shutil.which(p)])
def test_canario_real(prover):
    """Con Frama-C instalado el canario corre de verdad y devuelve una respuesta."""
    assert provers.demuestra_el_canario(shutil.which("frama-c"), prover) in (True, False)
