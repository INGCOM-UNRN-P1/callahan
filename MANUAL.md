# Manual de Uso y Referencia Técnica: callahan

> **CALLAHAN** — Verificador formal de contratos ACSL y especificaciones deductivas con Frama-C
> **Versión:** `0.1.0` · **CLI principal:** `callahan` · **Plugin Ripley:** `formal_contracts`

---

## 1. Arquitectura y Propósito Pedagógico

`callahan` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Verificación deductiva formal de código C basada en contratos ACSL (ANSI/ISO C Specification Language).
- Validación de precondiciones (`requires`), postcondiciones (`ensures`) y aserciones intermedias (`assert`).
- Comprobación matemática de invariantes de bucle (`loop invariant`) y variantes de terminación (`loop variant`).
- Control de contratos de enmarcado de memoria (`assigns`).
- Integración automatizada con Frama-C y el plugin WP (Weakest Precondition).

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Pruebas dinámicas basadas en ejecución de casos de test (delegado a `nostromo`).
- Generación de documentación técnica en Markdown/HTML (delegado a `corbel`).
- Verificación de cobertura estructural MC/DC (delegado a `dietrich`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install --editable /home/mrtin/dev/tools/callahan
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
callahan doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`callahan verify`](#verify) | Verifica deductivamente las precondiciones, postcondiciones e invariantes del archivo C. |
| [`callahan report`](#report) | Genera directamente la sección de reporte Markdown de CALLAHAN para Dredd. |
| [`callahan extract`](#extract) | Extrae e imprime las cláusulas de contratos ACSL encontradas en el código. |
| [`callahan doctor`](#doctor) | Comprueba si el entorno cuenta con Frama-C y provers SMT (Alt-Ergo, Z3). |

### `callahan verify`

Verifica deductivamente las precondiciones, postcondiciones e invariantes del archivo C.

Sale con 0 si todo se probó, 1 si Frama-C rechazó algún contrato y 2 si no se pudo
verificar (Frama-C no está instalado): un script distingue así una regresión real de
una dependencia opcional ausente.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C con anotaciones ACSL a verificar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Salida estructurada en JSON. |
| `--md`, `--output-md`, `-o` | `Optional[Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |

#### Ejemplo de Invocación
```bash
callahan verify <fuente>
```

### `callahan report`

Genera directamente la sección de reporte Markdown de CALLAHAN para Dredd.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C con contratos ACSL a verificar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[Path]` | `None` | Ruta de destino del archivo Markdown. |

#### Ejemplo de Invocación
```bash
callahan report <fuente>
```

### `callahan extract`

Extrae e imprime las cláusulas de contratos ACSL encontradas en el código.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `fuente` | `Path` | Archivo C a inspeccionar. |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `bool` | `False` | Salida en JSON. |

#### Ejemplo de Invocación
```bash
callahan extract <fuente>
```

### `callahan doctor`

Comprueba si el entorno cuenta con Frama-C y provers SMT (Alt-Ergo, Z3).

#### Ejemplo de Invocación
```bash
callahan doctor
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
callahan verify --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: callahan, tool=callahan, version=0.1.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`callahan` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
callahan doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.