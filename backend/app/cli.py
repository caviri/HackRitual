"""
HackRitual CLI — operational commands for managing a deployment.

Usage (after install)::

    hackritual --help
    hackritual serve
    hackritual migrate
    hackritual health

Usage with uv (without install)::

    uv run hackritual --help
"""

from __future__ import annotations

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="hackritual",
    help="HackRitual — an easy-to-summon platform for ritualised collaborative invention.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

console = Console()
err_console = Console(stderr=True, style="red")


# --------------------------------------------------------------------------- #
# serve
# --------------------------------------------------------------------------- #
@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Bind host."),
    port: int = typer.Option(7860, help="Bind port (HF Spaces default: 7860)."),
    reload: bool = typer.Option(False, "--reload", help="Enable hot-reload (dev only)."),
    workers: int = typer.Option(1, help="Number of uvicorn worker processes."),
) -> None:
    """
    Start the HackRitual API server with uvicorn.

    In production this is called by ``docker/entrypoint.sh``.
    In development use ``--reload`` for automatic code reloading.

    Examples::

        hackritual serve --reload
        hackritual serve --port 8080
    """
    import uvicorn

    console.print(f"[bold green]Starting HackRitual[/] on {host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_config=None,  # we configure logging ourselves
    )


# --------------------------------------------------------------------------- #
# migrate
# --------------------------------------------------------------------------- #
@app.command()
def migrate(
    revision: str = typer.Argument("head", help="Alembic revision target (default: head)."),
) -> None:
    """
    Run Alembic database migrations.

    Applies all pending migrations up to ``revision`` (default: ``head``).
    Safe to run on every startup — already-applied migrations are skipped.

    Examples::

        hackritual migrate
        hackritual migrate head
        hackritual migrate <revision_id>
    """
    from alembic import command
    from alembic.config import Config

    import os

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    console.print(f"[bold]Running migrations[/] → [cyan]{revision}[/]")
    try:
        command.upgrade(alembic_cfg, revision)
        console.print("[bold green]Migrations complete.[/]")
    except Exception as exc:
        err_console.print(f"Migration failed: {exc}")
        raise typer.Exit(code=1)


# --------------------------------------------------------------------------- #
# health
# --------------------------------------------------------------------------- #
@app.command()
def health(
    url: str = typer.Option(
        "http://localhost:7860",
        help="Base URL of the running HackRitual instance.",
    ),
) -> None:
    """
    Check the health of a running HackRitual instance.

    Calls ``GET /api/health`` and pretty-prints the response.
    Exits with code 1 if the check fails or the server is unreachable.

    Examples::

        hackritual health
        hackritual health --url https://my-space.hf.space
    """
    import urllib.request
    import json as _json

    endpoint = f"{url.rstrip('/')}/api/health"
    console.print(f"Checking [cyan]{endpoint}[/] ...")

    try:
        with urllib.request.urlopen(endpoint, timeout=10) as resp:
            data: dict = _json.loads(resp.read())
    except Exception as exc:
        err_console.print(f"Health check failed: {exc}")
        raise typer.Exit(code=1)

    table = Table(title="HackRitual Health", show_header=True)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    status_style = "green" if data.get("db_ok") else "red"
    storage_style = "green" if data.get("persistent_storage") else "yellow"

    table.add_row("status", f"[green]{data.get('status', '?')}[/]")
    table.add_row("version", str(data.get("version", "?")))
    table.add_row("event_id", str(data.get("event_id", "?")))
    table.add_row("event_state", str(data.get("event_state", "?")))
    table.add_row("db_ok", f"[{status_style}]{data.get('db_ok', '?')}[/]")
    table.add_row(
        "persistent_storage",
        f"[{storage_style}]{data.get('persistent_storage', '?')}[/]",
    )

    console.print(table)

    if not data.get("db_ok"):
        err_console.print("ERROR: database is not healthy.")
        raise typer.Exit(code=1)

    if not data.get("persistent_storage"):
        console.print(
            "[yellow]WARNING:[/] Storage is ephemeral — data will be lost on restart."
        )


# --------------------------------------------------------------------------- #
# info
# --------------------------------------------------------------------------- #
@app.command()
def info() -> None:
    """
    Print current configuration summary (non-secret fields only).

    Reads settings from the environment / .env file and displays them in
    a table.  Secret values (JWT_SECRET, SMTP_PASS, GITHUB_TOKEN) are
    masked to avoid accidental exposure.
    """
    try:
        from app.config import settings
    except Exception as exc:
        err_console.print(f"Failed to load settings: {exc}")
        raise typer.Exit(code=1)

    table = Table(title="HackRitual Configuration", show_header=True)
    table.add_column("Setting", style="bold")
    table.add_column("Value")

    _SECRET = "[dim]*** hidden ***[/]"

    rows: list[tuple[str, str]] = [
        ("app_base_url", settings.app_base_url),
        ("app_version", settings.app_version),
        ("log_level", settings.log_level),
        ("db_path", settings.db_path),
        ("upload_dir", settings.upload_dir),
        ("jwt_secret", _SECRET),
        ("jwt_algorithm", settings.jwt_algorithm),
        ("jwt_expire_minutes", str(settings.jwt_expire_minutes)),
        ("smtp_host", settings.smtp_host),
        ("smtp_port", str(settings.smtp_port)),
        ("smtp_user", settings.smtp_user),
        ("smtp_pass", _SECRET),
        ("smtp_from", settings.smtp_from),
        ("event_id", settings.event_id),
        ("event_title", settings.event_title),
        ("event_type", settings.event_type),
        ("event_start", str(settings.event_start)),
        ("event_end", str(settings.event_end)),
        ("admin_seed_emails", settings.admin_seed_emails or "[dim]not set[/]"),
        ("admin_setup_token", _SECRET if settings.admin_setup_token else "[dim]not set[/]"),
        ("github_export_repo", settings.github_export_repo or "[dim]not set[/]"),
        ("github_token", _SECRET if settings.github_token else "[dim]not set[/]"),
    ]
    for key, val in rows:
        table.add_row(key, val)

    console.print(table)
