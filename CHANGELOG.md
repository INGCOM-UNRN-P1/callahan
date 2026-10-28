# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versiones según [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado

- **verify**: demostrar también la ausencia de errores en tiempo de ejecución (`-wp-rte`: desbordes, accesos fuera de rango, divisiones por cero), con `--sin-rte` para desactivarlo y `--timeout` por meta (10 s; el de Frama-C es 2).
- **verify**: contraejemplos con valores concretos para las metas no demostradas («si el parámetro n recibe un valor negativo (ej: n = -1)»), confirmados con WP; `--sin-contraejemplos`.
- **check**: validar los contratos ACSL sin provers, con todos los errores explicados en español; `verify` lo hace antes de demostrar.
- **ejemplos**: algoritmos clásicos anotados que se demuestran completos (máximo, búsquedas lineal y binaria, promedio sin desborde, ordenamiento por inserción).
- **doctor**: avisar que Alt-Ergo < 2.5 sin z3 falla en las metas sobre memoria modificada.

### Corregido

- **verify**: una meta en estado `Failure` (falla del prover) se contaba como demostrada.
- **verify**: la caché de WP (`.frama-c/`) ya no se crea en la carpeta del alumno.

## [0.2.0] - 2026-09-28

Primera versión con registro de cambios; lo anterior está en el historial de git.

### Agregado

- **cli**: cumplir el contrato de línea de comandos de LINEAMIENTOS §3.2 (N-ECO-04) (`7e3fb4d`)

### Documentación

- agregar el texto de la licencia GPL-3.0-or-later que declara pyproject (N-ECO-06) (`fa1b2fb`)
- incorporar manual de uso integral y referencia tecnica (callahan) (`0c24558`)

### Mantenimiento

- **calidad**: verificar errores de Python y dependencias vulnerables (N-ECO-08, N-ECO-13) (`eea9e9d`)
