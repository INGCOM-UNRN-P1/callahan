"""Esqueletos ACSL desde docblocks y metas de Frama-C explicadas (QoL #101)."""

from typer.testing import CliRunner

from callahan.cli import app
from callahan.core.esqueletos import esqueletos_desde_docblocks, explicar_metas

CABECERA = """
/**
 * @brief Suma los n primeros elementos.
 * @param v el arreglo
 * @param n cuántos
 * @pre v != NULL
 * @pre n >= 0
 * @post el arreglo no cambia
 * @return la suma
 */
int sumar(const int *v, int n);

/**
 * @brief Limpia la lista.
 * @param l la lista
 */
void limpiar(Lista *l);
"""


def test_esqueletos():
    sumar, limpiar = esqueletos_desde_docblocks(CABECERA)
    assert "requires \\valid(v);" in sumar and "requires n >= 0;" in sumar
    assert "// TODO ensures: traducir «el arreglo no cambia»" in sumar
    assert "// ensures \\result" in sumar and sumar.rstrip().endswith("int sumar(const int *v, int n);")
    assert "// requires \\valid(l);" in limpiar and "ensures \\result" not in limpiar


def test_metas_explicadas():
    salida = ("[wp] [Alt-Ergo 2.4] Goal typed_sumar_ensures : Unknown (Qed:2ms)\n"
              "[wp] [Alt-Ergo 2.4] Goal typed_sumar_loop_invariant_preserved : Timeout (10s)\n"
              "[wp] [Alt-Ergo 2.4] Goal typed_sumar_assert_rte_mem_access : Unknown\n"
              "[wp] Proved goals:    5 / 8\n")
    metas = explicar_metas(salida)
    assert [m.estado for m in metas] == ["Unknown", "Timeout", "Unknown"]
    assert "poscondición" in metas[0].explicacion and "'sumar'" in metas[0].explicacion
    assert "-wp-timeout" in metas[1].explicacion and "acceso inválido" in metas[2].explicacion


def test_cli_skeleton(tmp_path):
    h = tmp_path / "s.h"
    h.write_text(CABECERA, encoding="utf-8")
    res = CliRunner().invoke(app, ["skeleton", str(h)])
    assert res.exit_code == 0 and res.stdout.count("/*@") == 2
