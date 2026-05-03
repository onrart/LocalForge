"""
CLI komutları — Click + Rich
"""

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def app():
    """{project_name} — {project_description}"""
    pass


@app.command()
def hello():
    """Basit bir karşılama komutu."""
    console.print(Panel.fit(
        "[bold green]{project_name}[/bold green] çalışıyor!",
        border_style="green",
    ))


if __name__ == "__main__":
    app()
