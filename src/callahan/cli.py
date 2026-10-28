"""CLI de CALLAHAN — Verificador formal de contratos ACSL con Frama-C."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer
from yutani.cli import crear_app
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from callahan import __version__
from callahan.core.acsl import TIMEOUT_POR_META, ErrorLectura, extraer_contratos_acsl, verificar_formal_frama_c

console = Console()
err_console = Console(stderr=True)

# Contrato de línea de comandos del ecosistema (-h/--help, --version/-v, errores de datos como
# mensajes) y textos de Typer en español, desde yutani (N-ECO-14).
app = crear_app(
    "callahan",
    __version__,
    "📜 CALLAHAN — Verificador formal de contratos ACSL (pre/post condiciones) y Frama-C WP.",
    add_completion=True,
)


def generar_seccion_markdown(reporte) -> str:
    """Genera sección de verificación formal ACSL para Dredd."""
    status = "ok" if reporte.ok else "fail"
    lines = [f"<!-- dredd-section: callahan, tool=callahan, version=1.0.0, status={status} -->\n## Verificación Formal de Contratos ACSL (Callahan)\n"]
    lines.append(f"- **Archivo analizado:** `{reporte.archivo.name}`")
    lines.append(f"- **Contratos formales detectados:** {len(reporte.contratos)}")
    total_prob = getattr(reporte, "total_clausulas_probadas", sum(len(c.clausulas) for c in reporte.contratos if c.verificado_wp))
    total_claus = getattr(reporte, "total_clausulas", sum(len(c.clausulas) for c in reporte.contratos))
    lines.append(f"- **Cláusulas verificadas con WP:** {total_prob}/{total_claus}\n")
    if reporte.errores_acsl:
        lines.append("> [!CAUTION]\n> **Contratos mal escritos:** Frama-C no pudo leer las anotaciones; no se intentó la demostración.\n")
        for e in reporte.errores_acsl:
            lugar = f"`{e.archivo}:{e.linea}`" if e.linea else f"`{e.archivo}`"
            lines.append(f"- {lugar}: {e.explicacion}")
        lines.append("")
        return "\n".join(lines)
    if not reporte.contratos:
        lines.append("> [!NOTE]\n> No se encontraron especificaciones formales ACSL (`/*@ ... */`) en el código.\n")
    elif not reporte.frama_c_disponible:
        lines.append("> [!WARNING]\n> **No Verificado (UNVERIFIED):** Frama-C no está disponible en el entorno; los contratos no fueron probados deductivamente.\n")
    elif reporte.ok:
        lines.append("> [!TIP]\n> **Demostración Exitosa:** Todas las precondiciones, postcondiciones e invariantes fueron probadas deductivamente.\n")
    else:
        lines.append("> [!WARNING]\n> **Verificación Incompleta:** Existen metas de prueba o contratos formales no satisfechos por Frama-C WP.\n")

    if reporte.contratos:
        lines.append("| Función | Línea | Cláusulas | Estado WP |")
        lines.append("| :--- | :---: | :---: | :---: |")
        for c in reporte.contratos:
            if not reporte.frama_c_disponible:
                wp_tag = "⚠️ UNVERIFIED (sin Frama-C)"
            else:
                wp_tag = "✓ Probado" if c.verificado_wp else "❌ No Probado"
            func_name = str(c.funcion).replace("|", "\\|")
            lines.append(f"| `{func_name}()` | {c.linea_inicio} | {len(c.clausulas)} | **{wp_tag}** |")
        lines.append("")
        contraejemplos = [c.contraejemplo for c in reporte.contratos if c.contraejemplo]
        if contraejemplos:
            lines.append("**Por qué no se demostró:**\n")
            lines.extend(f"- {ce.mensaje}" for ce in contraejemplos)
            lines.append("")
    return "\n".join(lines)


@app.command("verify")
def verify_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C con anotaciones ACSL a verificar."),
    header: Optional[Path] = typer.Option(None, "--header", "-H", help="Encabezado .h con docblocks Doxygen (@pre/@post) de corbel o contratos ACSL."),
    json_output: bool = typer.Option(False, "--json", help="Salida estructurada en JSON."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
    sin_rte: bool = typer.Option(False, "--sin-rte", help="No demostrar la ausencia de desbordes, accesos inválidos ni divisiones por cero: sólo el contrato."),
    timeout: int = typer.Option(TIMEOUT_POR_META, "--timeout", min=1, help="Segundos por meta para cada prover."),
    sin_contraejemplos: bool = typer.Option(False, "--sin-contraejemplos", help="No buscar con qué valores de los parámetros falla una meta (es más rápido)."),
) -> None:
    """Verifica deductivamente las precondiciones, postcondiciones e invariantes del archivo C.

    Además del contrato, demuestra que no hay desbordes de enteros, accesos fuera de rango ni
    divisiones por cero (salvo con --sin-rte). Antes valida que los contratos estén bien
    escritos (como `callahan check`), y si una meta no se demuestra busca con qué valores
    de los parámetros falla.

    Sale con 0 si todo se probó, 1 si Frama-C rechazó algún contrato (o están mal escritos)
    y 2 si no se pudo verificar (Frama-C no está instalado): un script distingue así una
    regresión real de una dependencia opcional ausente.
    """
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    if header is not None and not header.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el encabezado '{header}'.")
        raise typer.Exit(code=2)

    try:
        reporte = verificar_formal_frama_c(fuente, header=header, rte=not sin_rte, timeout=timeout,
                                           contraejemplos=not sin_contraejemplos)
    except ErrorLectura as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=2) from e

    if output_md:
        md_text = generar_seccion_markdown(reporte)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[green]✓ Sección Markdown generada en:[/green] [cyan]{output_md}[/cyan]")
        raise typer.Exit(code=reporte.codigo_de_salida)

    if json_output:
        print(json.dumps(reporte.to_dict(), indent=2, ensure_ascii=False))
        raise typer.Exit(code=reporte.codigo_de_salida)

    if reporte.errores_acsl:
        _mostrar_errores_acsl(reporte.errores_acsl)
        raise typer.Exit(code=reporte.codigo_de_salida)

    if not reporte.contratos:
        console.print(f"[yellow]No se encontraron contratos formales (/*@ ... */) en {fuente.name}.[/yellow]")
        raise typer.Exit(code=0)

    tabla = Table(title=f"Contratos ACSL Detectados en {fuente.name}")
    tabla.add_column("Función", style="bold cyan")
    tabla.add_column("Línea", justify="center")
    tabla.add_column("Cláusulas", justify="center")
    tabla.add_column("Verificación WP", justify="center")

    for c in reporte.contratos:
        if not reporte.frama_c_disponible:
            wp_str = "[yellow]UNVERIFIED (sin Frama-C)[/yellow]"
        else:
            wp_str = "[bold green]PROBADO (100%)[/bold green]" if c.verificado_wp else "[red]NO PROBADO[/red]"
        tabla.add_row(f"{c.funcion}()", str(c.linea_inicio), str(len(c.clausulas)), wp_str)

    console.print(tabla)
    for c in reporte.contratos:
        if c.contraejemplo:
            console.print(f"[bold red]✗[/bold red] {c.contraejemplo.mensaje}")
    explicaciones = [m.explicacion for m in reporte.metas
                     if not any(c.contraejemplo and f"_{c.funcion}_" in f"_{m.meta}_" for c in reporte.contratos)]
    for explicacion in dict.fromkeys(explicaciones):
        console.print(f"[yellow]•[/yellow] {explicacion}")
    if not reporte.frama_c_disponible:
        console.print("[yellow]Advertencia: Frama-C no está disponible en el entorno; verificación deductiva no realizada.[/yellow]")
    raise typer.Exit(code=reporte.codigo_de_salida)


@app.command("report")
def report_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C con contratos ACSL a verificar."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
) -> None:
    """Genera directamente la sección de reporte Markdown de CALLAHAN para Dredd."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    try:
        reporte = verificar_formal_frama_c(fuente)
    except ErrorLectura as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=2) from e
    md_content = generar_seccion_markdown(reporte)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


def _mostrar_errores_acsl(errores) -> None:
    for e in errores:
        lugar = f"{e.archivo}:{e.linea}" if e.linea else e.archivo
        console.print(f"[bold red]✗[/bold red] [cyan]{lugar}[/cyan] {e.explicacion}")
        console.print(f"  [dim]Frama-C: {e.mensaje}[/dim]")


@app.command("check")
def check_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C (o .h) con contratos ACSL."),
    json_output: bool = typer.Option(False, "--json", help="Salida en JSON."),
) -> None:
    """Valida que los contratos ACSL estén bien escritos, sin correr los provers.

    Lista todos los errores (no sólo el primero, como Frama-C) explicados: una variable
    que no existe, un punto y coma que falta, `=` en lugar de `==`. Sale con 1 si hay errores
    y con 2 si Frama-C no está instalado.
    """
    import tempfile

    from callahan.core.validacion import validar_anotaciones

    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    frama_c = shutil.which("frama-c")
    if not frama_c:
        err_console.print("[red]Error:[/red] Frama-C no está instalado (callahan doctor).")
        raise typer.Exit(code=2)
    with tempfile.TemporaryDirectory() as tmp:
        errores = validar_anotaciones(frama_c, fuente.resolve(), Path(tmp))
    for e in errores:
        if Path(e.archivo).name == fuente.name:
            e.archivo = str(fuente)
    if json_output:
        print(json.dumps({"schema_version": "1.0.0", "archivo": str(fuente), "ok": not errores,
                          "errores": [e.to_dict() for e in errores]}, indent=2, ensure_ascii=False))
    elif errores:
        _mostrar_errores_acsl(errores)
    else:
        console.print(f"[green]✓ Los contratos de {fuente.name} están bien escritos.[/green]")
    raise typer.Exit(code=1 if errores else 0)


@app.command("extract")
def extract_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a inspeccionar."),
    json_output: bool = typer.Option(False, "--json", help="Salida en JSON."),
) -> None:
    """Extrae e imprime las cláusulas de contratos ACSL encontradas en el código."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    try:
        contratos = extraer_contratos_acsl(fuente)
    except ErrorLectura as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=2) from e
    if json_output:
        print(json.dumps([c.to_dict() for c in contratos], indent=2, ensure_ascii=False))
        raise typer.Exit(code=0)

    for c in contratos:
        console.print(f"\n[bold cyan]Contrato para {c.funcion}()[/bold cyan] (Línea {c.linea_inicio}):")
        for cl in c.clausulas:
            console.print(f"  • [yellow]{cl.tipo}:[/yellow] {cl.expresion}")


@app.command("skeleton")
def skeleton_cmd(
    archivo: Path = typer.Argument(..., exists=True, dir_okay=False, help="Cabecera o fuente con prototipos documentados (@pre, @post)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Guardar los contratos en este archivo."),
) -> None:
    """Esqueletos de contratos ACSL a partir de los docblocks (@pre, @post, @param, @return)."""
    from callahan.core.esqueletos import esqueletos_desde_docblocks

    contratos = esqueletos_desde_docblocks(archivo.read_text(encoding="utf-8", errors="replace"))
    texto = "\n\n".join(contratos) + ("\n" if contratos else "")
    if output:
        output.write_text(texto, encoding="utf-8")
        console.print(f"[green]✓ {len(contratos)} contratos en {output}[/green]")
    elif contratos:
        print(texto, end="")
    else:
        console.print("[yellow]No hay prototipos documentados con /** ... */ (corbel scaffold genera los docblocks).[/yellow]")


@app.command("doctor")
def doctor_cmd(
    json_output: bool = typer.Option(False, "--json", help="Emitir el diagnóstico como JSON (schema_version 1.0.0)."),
) -> None:
    """Comprueba si el entorno cuenta con Frama-C y provers SMT (Alt-Ergo, Z3).

    Sale con 1 si falta Frama-C: sin él `callahan verify` no puede verificar.
    """
    from callahan import __version__

    chequeos = []
    for tool in ("frama-c", "alt-ergo", "z3", "why3"):
        ruta = shutil.which(tool)
        chequeos.append({"nombre": tool, "requerido": tool == "frama-c", "ok": bool(ruta),
                         "detalle": ruta or "No instalado"})
    ok = all(c["ok"] for c in chequeos if c["requerido"])
    aviso = _aviso_alt_ergo()
    if aviso:
        chequeos.append({"nombre": "alt-ergo (versión)", "requerido": False, "ok": False, "detalle": aviso})

    if json_output:
        print(json.dumps({"schema_version": "1.0.0", "herramienta": "callahan", "version": __version__,
                          "ok": ok, "chequeos": chequeos}, ensure_ascii=False, indent=2))
    else:
        tabla = Table(title="Herramientas de Verificación Deductiva")
        tabla.add_column("Prover / Motor", style="bold cyan")
        tabla.add_column("Estado", justify="center")
        tabla.add_column("Ruta")
        for c in chequeos:
            if c["ok"]:
                estado = "[green]✓ Presente[/green]"
            elif c["requerido"]:
                estado = "[bold red]✗ Requerido[/bold red]"
            else:
                estado = "[yellow]⚠️ Opcional[/yellow]"
            tabla.add_row(str(c["nombre"]), estado, str(c["detalle"]))
        console.print(tabla)
    if not ok:
        raise typer.Exit(code=1)


def _aviso_alt_ergo() -> Optional[str]:
    """Alt-Ergo < 2.5 sin z3: el Why3 de Frama-C le manda SMT2 polimórfico que no sabe leer."""
    import re
    import subprocess

    ruta = shutil.which("alt-ergo")
    if not ruta or shutil.which("z3"):
        return None
    try:
        salida = subprocess.run([ruta, "--version"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.match(r"\s*(\d+)\.(\d+)", salida)
    if m and (int(m.group(1)), int(m.group(2))) < (2, 5):
        return (f"Alt-Ergo {salida.strip()} falla (Failure) en las metas sobre memoria modificada, como un "
                "ordenamiento: instalá z3 o Alt-Ergo ≥ 2.5")
    return None


def main() -> None:
    app()


if __name__ == "__main__":
    main()
