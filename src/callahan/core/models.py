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
        if not self.frama_c_disponible:
            return False
        return all(c.verificado_wp for c in self.contratos) if self.contratos else True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "archivo": str(self.archivo),
            "total_contratos": len(self.contratos),
            "frama_c_disponible": self.frama_c_disponible,
            "ok": self.ok,
            "contratos": [c.to_dict() for c in self.contratos],
        }
