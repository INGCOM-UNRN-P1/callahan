"""Plugin de CALLAHAN para integración con RIPLEY."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List

from callahan.core.acsl import verificar_formal_frama_c


class CallahanPlugin:
    """Plugin de verificación formal de contratos ACSL para Ripley."""

    name = "formal_contracts"
    version = "0.1.0"

    def is_available(self) -> bool:
        return True

    def execute(self, workspace: Path, manifest_config: Dict[str, Any]) -> Dict[str, Any]:
        archivos = list(workspace.glob("*.c")) + list(workspace.glob("src/*.c"))
        observaciones = []
        total_contratos = 0

        for a in archivos:
            rep = verificar_formal_frama_c(a)
            total_contratos += len(rep.contratos)
            for c in rep.contratos:
                if not c.verificado_wp:
                    codigo = "FORMAL_WP_UNVERIFIED" if not rep.frama_c_disponible else "FORMAL_WP_FAILED"
                    severidad = "ADVERTENCIA" if not rep.frama_c_disponible else "ERROR"
                    observaciones.append({
                        "codigo": codigo,
                        "severidad": severidad,
                        "archivo": str(a),
                        "linea": c.linea_inicio,
                        "mensaje": f"No se pudo probar formalmente el contrato de la función '{c.funcion}': {c.mensaje_prover}",
                    })

        return {
            "ok": len(observaciones) == 0,
            "total_contratos": total_contratos,
            "observaciones": observaciones,
        }
