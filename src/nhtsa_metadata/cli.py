import json

import typer
from rich.console import Console

from nhtsa_metadata import __version__
from nhtsa_metadata.config import get_settings

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """NHTSA metadata catalog command line."""
    if ctx.invoked_subcommand is None:
        console.print(f"nhtsa_metadata {__version__}")


@app.command()
def version() -> None:
    """Print package version."""
    console.print(__version__)


@app.command()
def health() -> None:
    """Print Phase 0 health information without opening network connections."""
    settings = get_settings()
    payload = {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database_url_configured": bool(settings.database_url),
        "allow_live": settings.allow_live,
    }
    console.print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    app()
