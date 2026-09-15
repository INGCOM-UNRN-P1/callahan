"""Motor de análisis de contratos ACSL y verificación Frama-C en CALLAHAN."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from callahan.core.models import ClausulaContrato, ContratoACSL, ReporteVerificacion


def extraer_contratos_acsl(archivo: Path) -> List[ContratoACSL]:
    """Extrae bloques de contratos ACSL /*@ ... */ asociados a funciones C."""
    archivo = Path(archivo)
    if not archivo.is_file():
        return []

    try:
        contenido = archivo.read_text(encoding="utf-8")
    except Exception:
        return []

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
        for l in bloque_acsl.splitlines():
            l_str = l.strip()
            if m_cl := re.match(r"^@?\s*(requires|ensures|assigns|loop invariant|decreases)\s+(.+)", l_str):
                kw = m_cl.group(1)
                exp = m_cl.group(2).rstrip(";")
                clausulas.append(ClausulaContrato(
                    tipo=kw,
                    expresion=exp.strip(),
                    linea=linea_inicio,
                ))

        contratos.append(ContratoACSL(
            funcion=fn_name,
            archivo=archivo,
            linea_inicio=linea_inicio,
            clausulas=clausulas,
            verificado_wp=False,
        ))

    return contratos


def verificar_formal_frama_c(archivo: Path) -> ReporteVerificacion:
    """Ejecuta Frama-C WP sobre los contratos ACSL si el prover está disponible."""
    archivo = Path(archivo)
    contratos = extraer_contratos_acsl(archivo)
    frama_c = shutil.which("frama-c")

    if not frama_c:
        # Fallback sin prover: validación sintáctica de contratos, sin verificación deductiva
        for c in contratos:
            c.verificado_wp = False
            c.mensaje_prover = "UNVERIFIED: Frama-C no disponible"
        return ReporteVerificacion(
            archivo=archivo,
            contratos=contratos,
            frama_c_disponible=False,
        )

    cmd = [frama_c, "-wp", "-wp-prover", "alt-ergo,z3", str(archivo.resolve())]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        exito_wp = ("Proved goals: 100%" in res.stdout) or (res.returncode == 0)
        for c in contratos:
            c.verificado_wp = exito_wp
            c.mensaje_prover = res.stdout[:200]
    except Exception as e:
        for c in contratos:
            c.mensaje_prover = str(e)

    return ReporteVerificacion(
        archivo=archivo,
        contratos=contratos,
        frama_c_disponible=True,
    )
