"""Los algoritmos clásicos de `ejemplos/` se demuestran completos, con -wp-rte (Ola 23).

Ausencia de desbordes y accesos inválidos, terminación de cada lazo (loop variant) y, en el
ordenamiento, que el arreglo queda ordenado.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from callahan.core.acsl import verificar_formal_frama_c

EJEMPLOS = Path(__file__).resolve().parent.parent / "ejemplos"


def _alt_ergo_lee_memoria() -> bool:
    """Alt-Ergo < 2.5 falla con las metas sobre memoria modificada que genera el Why3 de Frama-C."""
    if shutil.which("z3"):
        return True
    if not shutil.which("alt-ergo"):
        return False
    m = re.match(r"\s*(\d+)\.(\d+)", subprocess.run(["alt-ergo", "--version"], capture_output=True, text=True).stdout)
    return bool(m) and (int(m.group(1)), int(m.group(2))) >= (2, 5)


con_wp = pytest.mark.skipif(not (shutil.which("frama-c") and (shutil.which("alt-ergo") or shutil.which("z3"))),
                            reason="requiere Frama-C y un prover")


@con_wp
@pytest.mark.parametrize("nombre", ["maximo.c", "busqueda_lineal.c", "busqueda_binaria.c", "promedio.c"])
def test_se_demuestra_completo(nombre):
    rep = verificar_formal_frama_c(EJEMPLOS / nombre, contraejemplos=False)
    assert rep.contratos and rep.ok, [m.explicacion for m in rep.metas]


@con_wp
@pytest.mark.skipif(not _alt_ergo_lee_memoria(), reason="requiere z3 o Alt-Ergo >= 2.5")
def test_el_ordenamiento_por_insercion_deja_el_arreglo_ordenado():
    rep = verificar_formal_frama_c(EJEMPLOS / "insercion.c", contraejemplos=False)
    assert rep.ok, [m.explicacion for m in rep.metas]


@con_wp
def test_con_alt_ergo_viejo_la_falla_del_prover_no_se_confunde_con_el_contrato():
    if _alt_ergo_lee_memoria():
        pytest.skip("el prover instalado demuestra el ordenamiento")
    rep = verificar_formal_frama_c(EJEMPLOS / "insercion.c")
    assert rep.metas and all(m.estado == "Failure" for m in rep.metas)
    assert "no es un problema del contrato" in rep.metas[0].explicacion
    assert rep.contratos[0].contraejemplo is None
