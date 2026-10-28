"""Contraejemplos con valores concretos para las metas que WP no demostró (Ola 23).

WP no da contraejemplos con Alt-Ergo, pero sí puede contestar preguntas más chicas.
Para una función con metas sin demostrar:

1. Se prueba de a una hipótesis sobre un parámetro (`n >= 0`, `n != 0`, `n > 0`,
   `\\valid(p)`) agregándola como `requires` en una segunda declaración (Frama-C junta
   los contratos de todas las declaraciones). Si con ella se demuestra todo, el problema
   está en los valores que la hipótesis excluye.
2. Para un parámetro entero se confirma un valor concreto: con `requires n == -1` se
   demuestra `ensures !(poscondición)`, es decir, que con ese valor la función la viola.
   Si no se puede confirmar, el mensaje no da ejemplo.

En las dos corridas se agrega `ensures \\false`: si eso se demuestra, la hipótesis
contradice al contrato (todo se demostraría en el vacío) y el resultado se descarta.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

# Recibe el texto C con la declaración agregada y devuelve las metas no demostradas
# (None si la corrida no sirvió: error de Frama-C, tiempo agotado).
Correr = Callable[[str], Optional[Set[str]]]

_MAX_PARAMETROS = 4
_ENTEROS = {"int", "long", "short", "char", "signed", "unsigned", "size_t"}

# (hipótesis, qué valores excluye, valor de ejemplo)
_HIPOTESIS_CON_SIGNO = [
    ("{p} >= 0", "un valor negativo", "-1"),
    ("{p} != 0", "cero", "0"),
    ("{p} > 0", "cero o un valor negativo", "0"),
]
_HIPOTESIS_SIN_SIGNO = [("{p} != 0", "cero", "0")]

_QUE_FALLA = [
    ("_ensures", "no asegura la postcondición"),
    ("_loop_invariant", "no mantiene el invariante de un lazo"),
    ("_loop_variant", "puede no terminar"),
    ("_rte_signed_overflow", "puede desbordar un entero"),
    ("_rte_mem_access", "puede acceder a memoria inválida"),
    ("_rte_division_by_zero", "puede dividir por cero"),
]


@dataclass
class Contraejemplo:
    funcion: str
    parametro: str
    hipotesis: str           # el requires que alcanza para demostrar todo
    ejemplo: Optional[str]   # valor confirmado con WP (sólo enteros)
    mensaje: str

    def to_dict(self) -> Dict[str, object]:
        return {"funcion": self.funcion, "parametro": self.parametro, "hipotesis": self.hipotesis,
                "ejemplo": self.ejemplo, "mensaje": self.mensaje}


@dataclass
class _Parametro:
    nombre: str
    tipo: str   # "entero", "sin_signo" o "puntero"
    solo_lectura: bool = False


def _definicion(texto: str, funcion: str) -> Optional[Tuple[str, str]]:
    """(tipo de retorno, parámetros) de la definición de la función en el texto."""
    m = re.search(rf"^(?P<tipo>[^\n;{{}}#]*?)\b{re.escape(funcion)}\s*\((?P<params>[^)]*)\)\s*\{{",
                  texto, re.MULTILINE)
    return (m.group("tipo").strip(), m.group("params")) if m else None


def _parametros(params: str) -> List[_Parametro]:
    resultado = []
    for p in params.split(","):
        p = p.strip()
        m = re.search(r"(\w+)\s*(\[[^\]]*\])?\s*$", p)
        if not m or p == "void":
            continue
        nombre, palabras = m.group(1), set(re.findall(r"\w+", p[:m.start(1)]))
        if "*" in p or m.group(2):
            resultado.append(_Parametro(nombre, "puntero", solo_lectura="const" in palabras))
        elif palabras & _ENTEROS:
            sin_signo = bool(palabras & {"unsigned", "size_t"})
            resultado.append(_Parametro(nombre, "sin_signo" if sin_signo else "entero"))
    return resultado


def ensures_del_contrato(textos: Sequence[str], funcion: str) -> Optional[List[str]]:
    """Las poscondiciones del contrato de la función; None si usa behaviors (no se pueden negar enteras)."""
    patron = re.compile(r"/\*@(?P<cuerpo>.*?)\*/\s*[^;{}()]*?\b" + re.escape(funcion) + r"\s*\(", re.DOTALL)
    for texto in textos:
        for m in patron.finditer(texto):
            cuerpo = "\n".join(re.sub(r"//.*$", "", ln).strip().lstrip("@").strip()
                               for ln in m.group("cuerpo").splitlines())
            if re.search(r"\bbehavior\b", cuerpo):
                return None
            clausulas = [c.strip() for c in cuerpo.split(";")]
            ensures = []
            for c in clausulas:
                m_e = re.match(r"ensures\s+(?:\w+\s*:(?!:)\s*)?(?P<exp>.+)$", c, re.DOTALL)
                if m_e:
                    ensures.append(" ".join(m_e.group("exp").split()))
            if ensures:
                return ensures
    return []


def _que_falla(metas: Sequence[str]) -> str:
    for clave, texto in _QUE_FALLA:
        if any(clave in m for m in metas):
            return texto
    return "no cumple su contrato"


def _declaracion(tipo: str, funcion: str, params: str, clausulas: Sequence[str]) -> str:
    cuerpo = "\n    ".join(clausulas)
    return f"\n/*@ {cuerpo}\n*/\n{tipo} {funcion}({params});\n"


def buscar_contraejemplo(texto_c: str, funcion: str, metas_fallidas: Sequence[str], correr: Correr,
                         textos_contrato: Sequence[str] = ()) -> Optional[Contraejemplo]:
    """Busca el parámetro y los valores con los que la función no cumple su contrato."""
    definicion = _definicion(texto_c, funcion)
    if definicion is None:
        return None
    tipo, params = definicion
    que_falla = _que_falla(metas_fallidas)

    for p in _parametros(params)[:_MAX_PARAMETROS]:
        candidatas: List[Tuple[str, Optional[str], Optional[str]]]
        if p.tipo == "puntero":
            valido = "\\valid_read" if p.solo_lectura else "\\valid"
            candidatas = [(f"{valido}({p.nombre})", None, None)]
        else:
            tabla = _HIPOTESIS_SIN_SIGNO if p.tipo == "sin_signo" else _HIPOTESIS_CON_SIGNO
            candidatas = [(h.format(p=p.nombre), desc, ej) for h, desc, ej in tabla]

        for hipotesis, descripcion, ejemplo in candidatas:
            fallidas = correr(texto_c + _declaracion(tipo, funcion, params, [
                f"requires callahan_hipotesis: {hipotesis};", "ensures callahan_vacio: \\false;"]))
            if fallidas is None:
                return None
            if [g for g in fallidas if not g.endswith("callahan_vacio")] or not fallidas:
                continue

            if descripcion is None:
                mensaje = f"La función {funcion} {que_falla} si el parámetro {p.nombre} no apunta a memoria válida."
                return Contraejemplo(funcion, p.nombre, hipotesis, None, mensaje + _sugerencia(hipotesis))

            confirmado = _confirmar(texto_c, tipo, funcion, params, p.nombre, ejemplo, metas_fallidas,
                                    correr, textos_contrato)
            mensaje = f"La función {funcion} {que_falla} si el parámetro {p.nombre} recibe {descripcion}"
            mensaje += f" (ej: {p.nombre} = {ejemplo})." if confirmado else "."
            return Contraejemplo(funcion, p.nombre, hipotesis, ejemplo if confirmado else None,
                                 mensaje + _sugerencia(hipotesis))
    return None


def _confirmar(texto_c: str, tipo: str, funcion: str, params: str, parametro: str, valor: Optional[str],
               metas_fallidas: Sequence[str], correr: Correr, textos_contrato: Sequence[str]) -> bool:
    """Demuestra que con `parametro == valor` la función viola sus poscondiciones."""
    if valor is None or not any("_ensures" in m for m in metas_fallidas):
        return False
    ensures = ensures_del_contrato([texto_c, *textos_contrato], funcion)
    if not ensures:
        return False
    negacion = "!(" + " && ".join(f"({e})" for e in ensures) + ")"
    fallidas = correr(texto_c + _declaracion(tipo, funcion, params, [
        f"requires callahan_hipotesis: {parametro} == {valor};",
        f"ensures callahan_testigo: {negacion};",
        "ensures callahan_vacio: \\false;"]))
    if fallidas is None:
        return False
    return (not any(g.endswith("callahan_testigo") for g in fallidas)
            and any(g.endswith("callahan_vacio") for g in fallidas))


def _sugerencia(hipotesis: str) -> str:
    return f" Agregá `requires {hipotesis};` al contrato o contemplá ese caso en el código."
