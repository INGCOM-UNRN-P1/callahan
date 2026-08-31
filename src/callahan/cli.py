"""CLI de CALLAHAN — Verificador formal de contratos ACSL con Frama-C."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from callahan import __version__
from callahan.core.acsl import extraer_contratos_acsl, verificar_formal_frama_c

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="callahan",
    help="📜 CALLAHAN — Verificador formal de contratos ACSL (pre/post condiciones) y Frama-C WP.",
    add_completion=True,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]CALLAHAN[/bold cyan] versión [bold]{__version__}[/bold]")
        raise typer.Exit(code=0)


@app.callback()
def main_callback(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de CALLAHAN.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


def generar_seccion_markdown(reporte) -> str:
    """Genera sección de verificación formal ACSL para Dredd."""
    lines = ["## Verificación Formal de Contratos ACSL (Callahan)\n"]
    lines.append(f"- **Archivo analizado:** `{reporte.archivo.name}`")
    lines.append(f"- **Contratos formales detectados:** {len(reporte.contratos)}")
    total_prob = getattr(reporte, "total_clausulas_probadas", sum(len(c.clausulas) for c in reporte.contratos if c.verificado_wp))
    total_claus = getattr(reporte, "total_clausulas", sum(len(c.clausulas) for c in reporte.contratos))
    lines.append(f"- **Cláusulas verificadas con WP:** {total_prob}/{total_claus}\n")
    if not reporte.contratos:
        lines.append("> [!NOTE]\n> No se encontraron especificaciones formales ACSL (`/*@ ... */`) en el código.\n")
    elif reporte.ok:
        lines.append("> [!TIP]\n> **Demostración Exitosa:** Todas las precondiciones, postcondiciones e invariantes fueron probadas deductivamente.\n")
    else:
        lines.append("> [!WARNING]\n> **Verificación Incompleta:** Existen metas de prueba o contratos formales no satisfechos por Frama-C WP.\n")

    if reporte.contratos:
        lines.append("| Función | Línea | Cláusulas | Estado WP |")
        lines.append("| :--- | :---: | :---: | :---: |")
        for c in reporte.contratos:
            wp_tag = "✓ Probado" if c.verificado_wp else "❌ No Probado"
            lines.append(f"| `{c.funcion}()` | {c.linea_inicio} | {len(c.clausulas)} | **{wp_tag}** |")
        lines.append("")
    return "\n".join(lines)


@app.command("verify")
def verify_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C con anotaciones ACSL a verificar."),
    json_output: bool = typer.Option(False, "--json", help="Salida estructurada en JSON."),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", "-o", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
) -> None:
    """Verifica deductivamente las precondiciones, postcondiciones e invariantes del archivo C."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)

    reporte = verificar_formal_frama_c(fuente)

    if output_md:
        md_text = generar_seccion_markdown(reporte)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[green]✓ Sección Markdown generada en:[/green] [cyan]{output_md}[/cyan]")
        raise typer.Exit(code=0 if reporte.ok else 1)

    if json_output:
        print(json.dumps(reporte.to_dict(), indent=2, ensure_ascii=False))
        raise typer.Exit(code=0 if reporte.ok else 1)

    if not reporte.contratos:
        console.print(f"[yellow]No se encontraron contratos formales (/*@ ... */) en {fuente.name}.[/yellow]")
        raise typer.Exit(code=0)

    tabla = Table(title=f"Contratos ACSL Detectados en {fuente.name}")
    tabla.add_column("Función", style="bold cyan")
    tabla.add_column("Línea", justify="center")
    tabla.add_column("Cláusulas", justify="center")
    tabla.add_column("Verificación WP", justify="center")

    for c in reporte.contratos:
        wp_str = "[bold green]PROBADO (100%)[/bold green]" if c.verificado_wp else "[red]NO PROBADO[/red]"
        tabla.add_row(f"{c.funcion}()", str(c.linea_inicio), str(len(c.clausulas)), wp_str)

    console.print(tabla)


@app.command("report")
def report_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C con contratos ACSL a verificar."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
) -> None:
    """Genera directamente la sección de reporte Markdown de CALLAHAN para Dredd."""
    if not fuente.is_file():
        err_console.print(f"[red]Error:[/red] No se encontró el archivo '{fuente}'.")
        raise typer.Exit(code=2)
    reporte = verificar_formal_frama_c(fuente)
    md_content = generar_seccion_markdown(reporte)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[green]✓ Reporte Markdown generado en:[/green] [cyan]{output}[/cyan]")
    else:
        print(md_content)


@app.command("extract")
def extract_cmd(
    fuente: Path = typer.Argument(..., help="Archivo C a inspeccionar."),
    json_output: bool = typer.Option(False, "--json", help="Salida en JSON."),
) -> None:
    """Extrae e imprime las cláusulas de contratos ACSL encontradas en el código."""
    contratos = extraer_contratos_acsl(fuente)
    if json_output:
        print(json.dumps([c.to_dict() for c in contratos], indent=2, ensure_ascii=False))
        raise typer.Exit(code=0)

    for c in contratos:
        console.print(f"\n[bold cyan]Contrato para {c.funcion}()[/bold cyan] (Línea {c.linea_inicio}):")
        for cl in c.clausulas:
            console.print(f"  • [yellow]{cl.tipo}:[/yellow] {cl.expresion}")


@app.command("doctor")
def doctor_cmd() -> None:
    """Comprueba si el entorno cuenta con Frama-C y provers SMT (Alt-Ergo, Z3)."""
    tabla = Table(title="Herramientas de Verificación Deductiva")
    tabla.add_column("Prover / Motor", style="bold cyan")
    tabla.add_column("Estado", justify="center")
    tabla.add_column("Ruta")

    for tool in ("frama-c", "alt-ergo", "z3", "why3"):
        p = shutil.which(tool)
        tabla.add_row(tool, "[green]✓ Presente[/green]" if p else "[yellow]⚠️ Opcional[/yellow]", p or "No instalado")

    console.print(tabla)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
