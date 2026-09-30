# 📜 CALLAHAN — Verificador Formal de Contratos ACSL en C

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

CALLAHAN realiza análisis y verificación deductiva de contratos formales de software en C escritos en lenguaje de especificación ACSL (`/*@ requires ... ensures ... */`) integrándose con Frama-C (WP).

---

## 🎯 Alcance

### Qué cubre
- Verificación deductiva formal de código C basada en contratos ACSL (ANSI/ISO C Specification Language).
- Validación de precondiciones (`requires`), postcondiciones (`ensures`) y aserciones intermedias (`assert`).
- Comprobación matemática de invariantes de bucle (`loop invariant`) y variantes de terminación (`loop variant`).
- Control de contratos de enmarcado de memoria (`assigns`).
- Integración automatizada con Frama-C y el plugin WP (Weakest Precondition).

### Qué no cubre (Límites y Delegación)
- Pruebas dinámicas basadas en ejecución de casos de test (delegado a `nostromo`).
- Generación de documentación técnica en Markdown/HTML (delegado a `corbel`).
- Verificación de cobertura estructural MC/DC (delegado a `dietrich`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Linux o Windows mediante WSL. Python >= 3.10.

### Dependencias Externas y Binarios
- `frama-c` con plugin `wp` y al menos un SMT prover (`alt-ergo` o `z3`; `verify` invoca `-wp-prover alt-ergo,z3`).

### Integración en el Ecosistema
- CLI `callahan`. Plugin registrado en `ripley.plugins` (`formal_contracts`). Subcomando `callahan doctor`.

---

## Uso Rápido

```bash
# 1. Extraer e inspeccionar contratos ACSL de un archivo
callahan extract algoritmo.c

# 2. Probar formalmente contratos con Frama-C
callahan verify algoritmo.c

# 2b. Generar la sección de reporte Markdown para Dredd
callahan report algoritmo.c -o callahan.md

# 3. Salida estructurada JSON
callahan extract algoritmo.c --json

# 4. Comprobar provers SMT disponibles (Z3, Alt-Ergo)
callahan doctor
```

<!-- p1:referencia:inicio — generado por p1-tools/scripts/readme_generado.py: no editar a mano -->

## Referencia rápida

### Requisitos

- Python ≥ 3.11 y [uv](https://docs.astral.sh/uv/getting-started/installation/).
- Programas del sistema: `frama-c`.

| Sistema | `frama-c` |
|:--|:--|
| Debian / Ubuntu | `opam install frama-c` |
| Fedora | `opam install frama-c` |
| Windows | no existe: usar WSL |
| macOS | `opam install frama-c` |

### Comandos

| Comando | Descripción |
|:--|:--|
| `callahan verify` | Verifica deductivamente las precondiciones, postcondiciones e invariantes del archivo C. |
| `callahan report` | Genera directamente la sección de reporte Markdown de CALLAHAN para Dredd. |
| `callahan extract` | Extrae e imprime las cláusulas de contratos ACSL encontradas en el código. |
| `callahan doctor` | Comprueba si el entorno cuenta con Frama-C y provers SMT (Alt-Ergo, Z3). |

Ayuda de cada comando: `callahan <comando> -h`.

<!-- p1:referencia:fin -->
