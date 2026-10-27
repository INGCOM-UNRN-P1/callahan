"""Motor de análisis de contratos ACSL y verificación Frama-C en CALLAHAN."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from callahan.core.esqueletos import explicar_metas, inyectar_acsl_desde_docblocks
from callahan.core.models import ClausulaContrato, ContratoACSL, ReporteVerificacion


class ErrorLectura(Exception):
    """El archivo fuente existe pero no se pudo leer (permisos o codificación)."""


def _expandir_docblocks(archivo: Path, contenido: str) -> str:
    if "/*@" in contenido or ("@pre" not in contenido and "@post" not in contenido and "@assigns" not in contenido):
        return contenido
    try:
        from corbel.core.acsl_exporter import inject_acsl_into_header  # type: ignore[import-not-found]
        expandido = inject_acsl_into_header(archivo)
        if "/*@" in expandido:
            return expandido
    except Exception:
        pass
    return inyectar_acsl_desde_docblocks(contenido)


def _extraer_de_texto(contenido: str, archivo: Path) -> List[ContratoACSL]:
    re_acsl_fn = re.compile(
        r"/\*@\s*([\s\S]*?)\s*\*/\s*(?:[a-zA-Z0-9_*]+\s+)+([a-zA-Z0-9_]+)\s*\([^)]*\)",
        re.MULTILINE,
    )

    contratos: List[ContratoACSL] = []

    for m in re_acsl_fn.finditer(contenido):
        bloque_acsl = m.group(1)
        fn_name = m.group(2)
        linea_inicio = contenido[:m.start()].count("\n") + 1

        clausulas: List[ClausulaContrato] = []
        linea_bloque = contenido[:m.start(1)].count("\n") + 1
        for offset, ln in enumerate(bloque_acsl.splitlines()):
            l_str = ln.strip().lstrip("*").strip()
            if m_cl := re.match(r"^@?\s*(requires|ensures|assigns|loop invariant|decreases)\s+(.+)", l_str):
                kw = m_cl.group(1)
                exp = m_cl.group(2).rstrip(";")
                clausulas.append(ClausulaContrato(
                    tipo=kw,
                    expresion=exp.strip(),
                    linea=linea_bloque + offset,
                ))

        contratos.append(ContratoACSL(
            funcion=fn_name,
            archivo=archivo,
            linea_inicio=linea_inicio,
            clausulas=clausulas,
            verificado_wp=False,
        ))

    return contratos


def extraer_contratos_acsl(archivo: Path) -> List[ContratoACSL]:
    """Extrae bloques de contratos ACSL /*@ ... */ (o docblocks @pre/@post de corbel) asociados a funciones C."""
    archivo = Path(archivo)
    if not archivo.is_file():
        return []

    try:
        contenido = archivo.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise ErrorLectura(f"No se pudo leer '{archivo}' como UTF-8: {e}") from e

    contratos = _extraer_de_texto(contenido, archivo)
    if not contratos and ("@pre" in contenido or "@post" in contenido or "@assigns" in contenido):
        expandido = _expandir_docblocks(archivo, contenido)
        contratos = _extraer_de_texto(expandido, archivo)
    return contratos


PROVERS_SOPORTADOS = ("alt-ergo", "z3")


def verificar_formal_frama_c(archivo: Path, header: Optional[Path] = None) -> ReporteVerificacion:
    """Ejecuta Frama-C WP sobre los contratos ACSL (incluyendo contratos exportados desde docblocks de corbel)."""
    archivo = Path(archivo)
    contratos = extraer_contratos_acsl(archivo)

    header_resuelto: Optional[Path] = Path(header) if header is not None else None
    if header_resuelto is None and archivo.is_file() and archivo.suffix == ".c":
        texto_c = archivo.read_text(encoding="utf-8", errors="replace")
        for m_inc in re.finditer(r'#\s*include\s*"([^"]+\.h)"', texto_c):
            cand_h = archivo.parent / m_inc.group(1)
            if cand_h.is_file():
                header_resuelto = cand_h
                break

    if header_resuelto is not None and header_resuelto.is_file():
        vistas = {c.funcion for c in contratos}
        for ch in extraer_contratos_acsl(header_resuelto):
            if ch.funcion not in vistas:
                vistas.add(ch.funcion)
                contratos.append(ch)

    frama_c = shutil.which("frama-c")
    provers = [p for p in PROVERS_SOPORTADOS if shutil.which(p)]

    if not frama_c or not provers:
        motivo = "Frama-C no disponible" if not frama_c else f"ningún prover instalado ({'/'.join(PROVERS_SOPORTADOS)})"
        for c in contratos:
            c.verificado_wp = False
            c.mensaje_prover = f"UNVERIFIED: {motivo}"
        return ReporteVerificacion(
            archivo=archivo,
            contratos=contratos,
            frama_c_disponible=False,
        )

    texto_orig = archivo.read_text(encoding="utf-8", errors="replace") if archivo.is_file() else ""
    texto_exp = _expandir_docblocks(archivo, texto_orig) if archivo.is_file() else ""
    h_orig = header_resuelto.read_text(encoding="utf-8", errors="replace") if (header_resuelto and header_resuelto.is_file()) else ""
    h_exp = _expandir_docblocks(header_resuelto, h_orig) if (header_resuelto and header_resuelto.is_file()) else ""
    requiere_tmp = (texto_exp != texto_orig) or (h_exp != h_orig) or (header is not None)

    try:
        if requiere_tmp and archivo.is_file():
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                if header_resuelto is not None and header_resuelto.is_file():
                    (tmp_path / header_resuelto.name).write_text(h_exp, encoding="utf-8")
                    if f'"{header_resuelto.name}"' not in texto_exp:
                        texto_exp = f'#include "{header_resuelto.name}"\n' + texto_exp
                tmp_c = tmp_path / archivo.name
                tmp_c.write_text(texto_exp, encoding="utf-8")
                cmd = [frama_c, "-wp", "-wp-prover", ",".join(provers), str(tmp_c)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        else:
            cmd = [frama_c, "-wp", "-wp-prover", ",".join(provers), str(archivo.resolve())]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        metas = explicar_metas(res.stdout)
        m_goals = re.search(r"Proved goals:\s*(\d+)\s*/\s*(\d+)", res.stdout)
        if m_goals:
            probadas, totales = int(m_goals.group(1)), int(m_goals.group(2))
            exito_wp = (res.returncode == 0) and (probadas == totales) and (totales > 0) and not metas
        elif "Proved goals: 100%" in res.stdout:
            exito_wp = (res.returncode == 0) and not metas
        else:
            exito_wp = (
                (res.returncode == 0)
                and not metas
                and "[Timeout]" not in res.stdout
                and "[Unknown]" not in res.stdout
                and "[Failed]" not in res.stdout
            )

        for c in contratos:
            propias = [m for m in metas if f"_{c.funcion}_" in f"_{m.meta}_"]
            c.verificado_wp = exito_wp and not propias
            c.mensaje_prover = "\n".join(m.explicacion for m in propias) or res.stdout[:200]
    except Exception as e:
        for c in contratos:
            c.mensaje_prover = str(e)

    return ReporteVerificacion(
        archivo=archivo,
        contratos=contratos,
        frama_c_disponible=True,
    )
