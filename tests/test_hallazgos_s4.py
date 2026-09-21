"""Regresiones de CALLAHAN-D0302, D0304, D0401 y D0402."""

from typer.testing import CliRunner

from callahan.cli import app
from callahan.core.acsl import ErrorLectura, extraer_contratos_acsl

runner = CliRunner()

FUENTE = """/*@
  requires n > 0;
  ensures \\result >= 0;
  assigns \\nothing;
*/
int f(int n) { return n; }
"""


def test_cada_clausula_tiene_su_linea_real(tmp_path):
    f = tmp_path / "a.c"
    f.write_text(FUENTE)
    lineas = [c.linea for c in extraer_contratos_acsl(f)[0].clausulas]
    assert lineas == [2, 3, 4]


def test_encoding_invalido_no_se_traga_en_silencio(tmp_path):
    f = tmp_path / "a.c"
    f.write_bytes(b"/*@ requires n > 0; */ int f(int n) { return '\xe9'; }\n")
    try:
        extraer_contratos_acsl(f)
    except ErrorLectura:
        pass
    else:
        raise AssertionError("debió lanzar ErrorLectura")
    res = runner.invoke(app, ["extract", str(f)])
    assert res.exit_code == 2


def test_extract_de_archivo_inexistente_sale_2(tmp_path):
    res = runner.invoke(app, ["extract", str(tmp_path / "nada.c")])
    assert res.exit_code == 2


def test_doctor_marca_frama_c_como_requerido(monkeypatch):
    monkeypatch.setattr("callahan.cli.shutil.which", lambda t: None)
    res = runner.invoke(app, ["doctor"])
    assert "Requerido" in res.stdout
