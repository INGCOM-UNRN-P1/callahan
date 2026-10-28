"""Validación de las anotaciones ACSL antes de llamar a los provers (Ola 23).

Frama-C aborta en el primer error de un contrato y lo informa en inglés
(`unbound logic variable m. Ignoring logic specification of function f`). Con
`-kernel-warn-key annot-error=active` sigue leyendo y lista todos: acá se corre así,
sin WP, y cada mensaje se traduce a qué está mal en el contrato y cómo se arregla.

gcc no sirve para esto (los `/*@ … */` son comentarios para él): la única forma de
saber si un contrato está bien escrito es el analizador de Frama-C. Los errores de C
(sintaxis, un `#include` que no está) se derivan a `daedalus compile`, que los explica.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence


@dataclass
class ErrorAnotacion:
    archivo: str
    linea: Optional[int]
    mensaje: str          # el de Frama-C, tal cual
    explicacion: str
    tipo: str = "acsl"    # "acsl" (el contrato) o "c" (el código no compila)

    def to_dict(self) -> Dict[str, object]:
        return {"archivo": self.archivo, "linea": self.linea, "tipo": self.tipo,
                "mensaje": self.mensaje, "explicacion": self.explicacion}


_TRADUCCIONES = [
    (r"unbound logic variable (\w+)",
     "`{0}` no está declarada: un contrato sólo puede nombrar parámetros de la función, variables "
     "globales o variables ligadas con \\forall/\\exists. ¿Es un error de tipeo?"),
    (r"unbound logic (?:function|predicate) (\w+)",
     "`{0}` no es una función lógica ni un predicado definido: declaralo antes con "
     "/*@ logic … */ o /*@ predicate … */ (desde un contrato no se puede llamar a funciones de C)."),
    (r"\\result meaningless",
     "`\\result` sólo vale en un ensures de una función que devuelve algo: no en un requires "
     "ni en una función void."),
    (r"(\S+) is not a pointer",
     "`{0}` no es un puntero: \\valid, \\valid_read y * sólo se aplican a punteros."),
    (r"invalid type (.+) for `unary \*'",
     "Se desreferencia con * algo que no es un puntero (es de tipo {0})."),
    (r"expecting '(.+)' before (\S+)",
     "Falta `{0}` antes de `{1}`: cada cláusula (requires, ensures, assigns…) termina con punto y coma."),
    (r"unexpected token '(.+)'",
     "Símbolo `{0}` inesperado: revisá que no falte un operando o un paréntesis."),
    (r"Assignment operators not allowed",
     "En un contrato `=` no compara: usá `==`."),
    (r"Attribute annotation '(\S+)'",
     "`{0}` no es una palabra de ACSL: ¿quisiste escribir requires, ensures, assigns o decreases?"),
]

# [kernel:annot-error] archivo.c:6: Warning: expecting ';' before ensures
_UBICACION = re.compile(r"^\[kernel(?::[\w-]+)?\]\s+(?P<archivo>[^\s:]+):(?P<linea>\d+):\s*(?:Warning:|Failure:)?\s*(?P<resto>.*)$")


def _traducir(mensaje: str) -> str:
    for patron, texto in _TRADUCCIONES:
        m = re.search(patron, mensaje)
        if m:
            explicacion = texto.format(*m.groups())
            break
    else:
        explicacion = f"Frama-C no entiende esta anotación: {mensaje}"
    m_fn = re.search(r"Ignoring logic specification of function (\w+)", mensaje)
    if m_fn:
        explicacion += f" Hasta que lo corrijas, Frama-C ignora el contrato entero de {m_fn.group(1)}."
    return explicacion


def _mensajes(salida: str) -> List[str]:
    """Agrupa la salida en mensajes: cada uno empieza con `[` y sigue en las líneas con sangría."""
    mensajes: List[str] = []
    for linea in salida.splitlines():
        if linea.startswith("[") or not mensajes:
            mensajes.append(linea)
        else:
            mensajes[-1] += "\n" + linea
    return mensajes


def analizar_salida_kernel(salida: str) -> List[ErrorAnotacion]:
    """Errores de anotación y de C en la salida de `frama-c` (sin WP)."""
    errores: List[ErrorAnotacion] = []
    for bloque in _mensajes(salida):
        cabecera, _, cuerpo = bloque.partition("\n")
        m = _UBICACION.match(cabecera)
        if cabecera.startswith("[kernel:annot-error]") and m:
            texto = " ".join(p.strip() for p in [m.group("resto"), cuerpo] if p.strip())
            errores.append(ErrorAnotacion(m.group("archivo"), int(m.group("linea")), texto, _traducir(texto)))
        elif m and "syntax error" in cuerpo:
            errores.append(ErrorAnotacion(
                m.group("archivo"), int(m.group("linea")), "syntax error",
                "El código C tiene un error de sintaxis (o una anotación que Frama-C no pudo ubicar): "
                "compilalo con `daedalus compile` para ver la causa.", tipo="c"))
        elif cabecera.startswith("[kernel] User Error: failed to run:"):
            fatal = re.search(r"^(?P<archivo>[^\s:]+):(?P<linea>\d+):\d+: fatal error: (?P<msg>.+)$", salida, re.MULTILINE)
            errores.append(ErrorAnotacion(
                Path(fatal.group("archivo")).name if fatal else "", int(fatal.group("linea")) if fatal else None,
                fatal.group("msg") if fatal else "falló el preprocesador",
                "No se pudo preprocesar el archivo (por ejemplo, un #include que no se encuentra): "
                "compilalo con `daedalus compile` para ver la causa.", tipo="c"))
    return errores


def validar_anotaciones(frama_c: str, fuente: Path, cwd: Path, extra: Sequence[str] = (),
                        timeout: int = 60) -> List[ErrorAnotacion]:
    """Corre el analizador de Frama-C sin provers y devuelve los errores de los contratos."""
    cmd = [frama_c, "-kernel-warn-key", "annot-error=active", *extra, str(fuente)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    errores = analizar_salida_kernel(res.stdout + "\n" + res.stderr)
    if res.returncode != 0 and not errores:
        ultima = next((ln for ln in reversed((res.stdout + res.stderr).splitlines()) if ln.strip()), "")
        errores.append(ErrorAnotacion(fuente.name, None, ultima, f"Frama-C no pudo leer el archivo: {ultima}", tipo="c"))
    return errores
