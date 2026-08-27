# 📜 CALLAHAN — Verificador Formal de Contratos ACSL en C

CALLAHAN realiza análisis y verificación deductiva de contratos formales de software en C escritos en lenguaje de especificación ACSL (`/*@ requires ... ensures ... */`) integrándose con Frama-C (WP).

## Uso Rápido

```bash
# 1. Extraer e inspeccionar contratos ACSL de un archivo
callahan extract algoritmo.c

# 2. Probar formalmente contratos con Frama-C
callahan verify algoritmo.c

# 3. Salida estructurada JSON
callahan extract algoritmo.c --json

# 4. Comprobar provers SMT disponibles (Z3, Alt-Ergo)
callahan doctor
```
