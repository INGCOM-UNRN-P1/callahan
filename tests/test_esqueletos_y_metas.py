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


def test_metas_formato_moderno_frama_c():
    salida = (
        "[wp] [Timeout] typed_doble_ensures (Qed 0.50ms) (Alt-Ergo)\n"
        "[wp] Proved goals:    2 / 3\n"
    )
    metas = explicar_metas(salida)
    assert len(metas) == 1
    assert metas[0].estado == "Timeout"
    assert "'doble'" in metas[0].explicacion


def test_verify_con_header_corbel_docblocks(tmp_path):
    import json
    import shutil

    h = tmp_path / "acumulador.h"
    h.write_text(
        "#ifndef ACUM_H\n"
        "#define ACUM_H\n"
        "typedef struct acum { int total; } acum_t;\n"
        "/**\n"
        " * @brief Suma un valor positivo al acumulador.\n"
        " * @param a Puntero al acumulador.\n"
        " * @param delta Incremento.\n"
        " * @return Nuevo total.\n"
        " * @pre a != NULL\n"
        " * @pre delta >= 0 && delta <= 100\n"
        " * @pre a->total >= 0 && a->total <= 1000\n"
        " * @assigns a->total\n"
        " * @post a->total == \\old(a->total) + delta\n"
        " * @post return == a->total\n"
        " */\n"
        "int acum_sumar(acum_t *a, int delta);\n"
        "#endif\n",
        encoding="utf-8",
    )

    c_ok = tmp_path / "acumulador.c"
    c_ok.write_text(
        '#include "acumulador.h"\n'
        "int acum_sumar(acum_t *a, int delta) {\n"
        "    a->total = a->total + delta;\n"
        "    return a->total;\n"
        "}\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    res_extract = runner.invoke(app, ["extract", str(h), "--json"])
    assert res_extract.exit_code == 0
    extraidos = json.loads(res_extract.stdout)
    assert len(extraidos) == 1
    assert extraidos[0]["funcion"] == "acum_sumar"

    if shutil.which("frama-c") and shutil.which("alt-ergo"):
        res_ok = runner.invoke(app, ["verify", str(c_ok), "--header", str(h), "--json"])
        assert res_ok.exit_code == 0
        datos_ok = json.loads(res_ok.stdout)
        assert datos_ok["ok"] is True
        assert datos_ok["contratos"][0]["verificado_wp"] is True

        c_mal = tmp_path / "acumulador_mal.c"
        c_mal.write_text(
            '#include "acumulador.h"\n'
            "int acum_sumar(acum_t *a, int delta) {\n"
            "    a->total = a->total - delta - 1;\n"
            "    return a->total;\n"
            "}\n",
            encoding="utf-8",
        )
        res_mal = runner.invoke(app, ["verify", str(c_mal), "--header", str(h), "--json"])
        assert res_mal.exit_code == 1
        datos_mal = json.loads(res_mal.stdout)
        assert datos_mal["ok"] is False
        assert datos_mal["contratos"][0]["verificado_wp"] is False

