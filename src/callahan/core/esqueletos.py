"""Esqueletos ACSL desde la documentación y metas de Frama-C explicadas (revisión 07, callahan).

- `esqueletos_desde_docblocks`: de cada prototipo documentado (`@pre`, `@post`, `@param`,
  `@return`) arma el contrato ACSL para completar. Lo que ya es una expresión de C (`n > 0`,
  `p != NULL`) se traduce; lo que es prosa queda como `TODO` con el texto original.
- `explicar_metas`: las líneas `Goal … : Unknown/Timeout/Failed` de Frama-C WP, en español y con
  qué suele faltar (QoL #101).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

_DOCBLOCK_Y_PROTOTIPO = re.compile(
    r"/\*\*(?P<doc>.*?)\*/\s*(?P<proto>[A-Za-z_][\w\s\*]*?\b(?P<nombre>[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)\s*[;{])",
    re.DOTALL)
_EXPRESION_C = re.compile(r"^[\w\s\[\]\.\->*&!=<>+\-/%()|]+$")


def _etiquetas(doc: str, etiqueta: str) -> List[str]:
    lineas = [l.strip().lstrip("*").strip() for l in doc.splitlines()]
    return [l[len(etiqueta):].strip() for l in lineas if l.startswith(etiqueta)]


def _a_acsl(texto: str) -> Optional[str]:
    """Una condición escrita en C como predicado ACSL; None si es prosa."""
    t = texto.rstrip(".").strip()
    m = re.fullmatch(r"(\w+)\s*!=\s*NULL", t)
    if m:
        return f"\\valid({m.group(1)})"
    t = re.sub(r"\bNULL\b", "\\\\null", t)
    if _EXPRESION_C.match(t) and re.search(r"[=<>!]", t):
        return t
    return None


def _clausulas(tipo: str, textos: List[str]) -> List[str]:
    resultado = []
    for texto in textos:
        acsl = _a_acsl(texto)
        resultado.append(f"  {tipo} {acsl};" if acsl else f"  // TODO {tipo}: traducir «{texto}» a ACSL")
    return resultado


def esqueletos_desde_docblocks(codigo: str) -> List[str]:
    contratos = []
    for m in _DOCBLOCK_Y_PROTOTIPO.finditer(codigo):
        doc, nombre, params = m.group("doc"), m.group("nombre"), m.group("params")
        lineas = [f"/*@ // Contrato de {nombre} (esqueleto generado por callahan: revisalo)"]
        punteros = re.findall(r"\*\s*(\w+)\s*(?:,|$)", params)
        pre = _etiquetas(doc, "@pre")
        lineas += _clausulas("requires", pre)
        for p in punteros:
            if not any(p in x for x in pre):
                lineas.append(f"  // requires \\valid({p});  ← si {p} no puede ser NULL")
        lineas.append("  assigns \\nothing;  // ← cambialo si la función modifica memoria")
        lineas += _clausulas("ensures", _etiquetas(doc, "@post"))
        if _etiquetas(doc, "@return") and not m.group("proto").lstrip().startswith("void"):
            lineas.append(f"  // ensures \\result ... ;  ← {_etiquetas(doc, '@return')[0]}")
        lineas.append("*/")
        contratos.append("\n".join(lineas) + "\n" + m.group("proto").rstrip("{").rstrip().rstrip(";") + ";")
    return contratos


@dataclass
class MetaNoDemostrada:
    meta: str
    estado: str
    explicacion: str


_META = re.compile(r"Goal\s+(?P<meta>\S+)\s*(?:\([^)]*\))?\s*:\s*(?P<estado>Unknown|Timeout|Failed|Stepout)", re.IGNORECASE)
_EXPLICACIONES = [
    ("_ensures", "No se pudo demostrar la poscondición (ensures) de {f}: puede que falte una precondición (requires) que la garantice, o que el código no cumpla lo que promete el contrato."),
    ("_loop_invariant_preserved", "El invariante de un lazo de {f} no se mantiene en cada vuelta: revisá que el cuerpo lo conserve o debilitalo."),
    ("_loop_invariant_established", "El invariante de un lazo de {f} no vale antes de entrar: revisá la inicialización de las variables del lazo."),
    ("_loop_variant", "No se pudo demostrar que un lazo de {f} termina: agregá un loop variant que decrezca en cada vuelta."),
    ("_assigns", "{f} modifica memoria que el contrato no declara en assigns."),
    ("_call_", "Una llamada dentro de {f} no cumple la precondición (requires) de la función llamada."),
    ("_rte_mem_access", "Posible acceso inválido a memoria en {f} (puntero nulo o índice fuera de rango): agregá un requires \\valid(...) o verificá el índice."),
    ("_rte_signed_overflow", "Posible desborde de enteros con signo en {f}: acotá los valores con un requires."),
    ("_rte_division_by_zero", "Posible división por cero en {f}: agregá un requires que lo excluya."),
]


def _funcion_de(meta: str) -> str:
    m = re.match(r"typed_(?:ref_)?(\w+?)_(?:ensures|loop|assigns|call|rte|requires|assert|terminates)", meta)
    return m.group(1) if m else meta


def explicar_metas(salida_frama_c: str) -> List[MetaNoDemostrada]:
    metas = []
    for m in _META.finditer(salida_frama_c):
        meta, estado = m.group("meta"), m.group("estado").capitalize()
        f = f"'{_funcion_de(meta)}'"
        texto = next((e.format(f=f) for clave, e in _EXPLICACIONES if clave in meta),
                     f"El prover no pudo demostrar la meta {meta} de {f}.")
        if estado == "Timeout":
            texto += " (Se agotó el tiempo: a veces alcanza con más tiempo, -wp-timeout.)"
        metas.append(MetaNoDemostrada(meta, estado, texto))
    return metas
