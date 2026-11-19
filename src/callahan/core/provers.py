"""Provers en los que se puede confiar: un canario que ninguno debe demostrar.

Un prover que demuestra una meta falsa vuelve inútil la verificación: todo contrato sale
«probado». Pasa, por ejemplo, con Z3 4.16 y el Why3 de Frama-C 33: los axiomas que le manda
WP (módulo entero, conversiones a 128 bits) le resultan contradictorios y desde ahí demuestra
cualquier cosa. Antes de usar un prover, callahan le pide demostrar una poscondición falsa
(`absol` que promete devolver `n` tal cual); si la demuestra, no se usa.

El resultado se guarda en `$XDG_CACHE_HOME/callahan/provers.json`, por ruta, tamaño y fecha del
prover y de Frama-C: se recalcula solo cuando alguno de los dos cambia (una actualización).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CANARIO = (
    "/*@ assigns \\nothing;\n"
    "    ensures \\result == n; */\n"
    "int callahan_canario(int n) { return n < 0 ? -n : n; }\n"
)
_TIMEOUT_CANARIO = 1  # segundos por meta: un prover inconsistente la demuestra en milisegundos
_TIMEOUT_TOTAL = 60


def _archivo_cache() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "callahan" / "provers.json"


def _huella(*rutas: str) -> str:
    partes = []
    for ruta in rutas:
        try:
            st = Path(ruta).resolve().stat()
            partes.append(f"{Path(ruta).resolve()}:{st.st_size}:{int(st.st_mtime)}")
        except OSError:
            partes.append(f"{ruta}:?")
    return "|".join(partes)


def _leer_cache() -> Dict[str, bool]:
    try:
        datos = json.loads(_archivo_cache().read_text(encoding="utf-8"))
        return {k: bool(v) for k, v in datos.items()} if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def _guardar_cache(datos: Dict[str, bool]) -> None:
    try:
        destino = _archivo_cache()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(datos, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        pass  # sin caché se vuelve a probar la próxima vez: no es un error


def demuestra_el_canario(frama_c: str, prover: str) -> Optional[bool]:
    """True si `prover` demuestra la meta falsa; None si no se pudo saber (Frama-C no corrió)."""
    with tempfile.TemporaryDirectory() as tmp:
        fuente = Path(tmp) / "callahan_canario.c"
        fuente.write_text(CANARIO, encoding="utf-8")
        try:
            res = subprocess.run(
                [frama_c, "-wp", "-wp-prover", prover, "-wp-timeout", str(_TIMEOUT_CANARIO),
                 "-wp-cache", "none", "-wp-fct", "callahan_canario", str(fuente)],
                capture_output=True, text=True, timeout=_TIMEOUT_TOTAL, cwd=tmp,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
    m = re.search(r"Proved goals:\s*(\d+)\s*/\s*(\d+)", res.stdout)
    if not m:
        return None
    return int(m.group(1)) == int(m.group(2))


def prover_confiable(frama_c: str, prover: str) -> bool:
    """El prover no demuestra la meta falsa. Si no se pudo averiguar, se lo da por confiable."""
    ruta = shutil.which(prover)
    if not ruta:
        return False
    clave = f"{prover}|{_huella(ruta, frama_c)}"
    cache = _leer_cache()
    if clave in cache:
        return cache[clave]
    demuestra = demuestra_el_canario(frama_c, prover)
    if demuestra is None:
        return True  # sin respuesta no se guarda: se vuelve a probar la próxima vez
    cache[clave] = not demuestra
    _guardar_cache(cache)
    return not demuestra


def separar_provers(frama_c: str, provers: List[str]) -> Tuple[List[str], List[str]]:
    """(confiables, descartados) entre los provers instalados."""
    confiables: List[str] = []
    descartados: List[str] = []
    for p in provers:
        (confiables if prover_confiable(frama_c, p) else descartados).append(p)
    return confiables, descartados


def version_prover(prover: str) -> str:
    """Versión que informa el prover (para los avisos), o su nombre si no responde."""
    ruta = shutil.which(prover)
    if not ruta:
        return prover
    try:
        salida = subprocess.run([ruta, "--version"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return prover
    m = re.search(r"\d+(?:\.\d+)+", salida)
    nombre = {"z3": "Z3", "alt-ergo": "Alt-Ergo"}.get(prover, prover)
    return f"{nombre} {m.group(0)}" if m else nombre


def aviso_descartado(prover: str) -> str:
    return (f"{version_prover(prover)} demuestra metas falsas con este Frama-C (daría por probado "
            "cualquier contrato): callahan no lo usa. Instalá otra versión o usá otro prover.")
