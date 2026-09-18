"""Modelos de datos para contratos ACSL y verificación deductiva en CALLAHAN."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ClausulaContrato:
    tipo: str                   # "requires", "ensures", "assigns", "loop invariant"
    expresion: str
    linea: int


@dataclass
class ContratoACSL:
    funcion: str
    archivo: Path
    linea_inicio: int
    clausulas: List[ClausulaContrato] = field(default_factory=list)
    verificado_wp: bool = False
    mensaje_prover: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "funcion": self.funcion,
            "archivo": str(self.archivo),
            "linea": self.linea_inicio,
            "total_clausulas": len(self.clausulas),
            "clausulas": [{"tipo": c.tipo, "exp": c.expresion, "linea": c.linea} for c in self.clausulas],
            "verificado_wp": self.verificado_wp,
            "mensaje_prover": self.mensaje_prover,
        }


@dataclass
class ReporteVerificacion:
    archivo: Path
    contratos: List[ContratoACSL] = field(default_factory=list)
    frama_c_disponible: bool = False

    @property
    def ok(self) -> bool:
        # Sin contratos no hay nada que verificar: con o sin Frama-C.
        if not self.contratos:
            return True
        if not self.frama_c_disponible:
            return False
        return all(c.verificado_wp for c in self.contratos)

    @property
    def verificacion_imposible(self) -> bool:
        """Hay contratos pero falta Frama-C: no se pudo verificar (≠ se verificó y falló)."""
        return bool(self.contratos) and not self.frama_c_disponible

    @property
    def codigo_de_salida(self) -> int:
        """Contrato 0/1/2 de la CLI: 0 verificado, 1 contrato rechazado, 2 no se pudo verificar."""
        if self.verificacion_imposible:
            return 2
        return 0 if self.ok else 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "archivo": str(self.archivo),
            "total_contratos": len(self.contratos),
            "frama_c_disponible": self.frama_c_disponible,
            "ok": self.ok,
            "contratos": [c.to_dict() for c in self.contratos],
        }
