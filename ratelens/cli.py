"""The ``ratelens`` command."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .export import FORMATS, render
from .loader import DataError, load_rate_limits
from .lookup import apis, find_limits, normalise_path, search
from .model import RateLimit
from .planner import format_duration, group_by_scope, make_plan


class Context:
    def __init__(self, data_path: Path | None) -> None:
        self.data_path = data_path
        self._data: list[RateLimit] | None = None

    @property
    def data(self) -> list[RateLimit]:
        if self._data is None:
            self._data = load_rate_limits(self.data_path)
        return self._data


class Group(click.Group):
    """Turns data-file problems into a one-line error and exit status 1."""

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except FileNotFoundError as exc:
            raise click.ClickException(f"Data file not found at {_missing_path(exc)}") from exc
        except DataError as exc:
            raise click.ClickException(str(exc)) from exc


def _missing_path(exc: FileNotFoundError) -> str:
    text = str(exc)
    return text.split(" at ", 1)[1] if " at " in text else text


def _line(item: RateLimit) -> str:
    who = f"  ({item.scope})" if item.scope else ""
    return f"{item.allowance:<14}{item.requests_per_minute:>9g}/min  {item.endpoint}{who}"


@click.group(cls=Group)
@click.option(
    "--data",
    "data_path",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Use this CSV instead of the bundled dataset.",
)
@click.version_option(__version__, prog_name="ratelens")
@click.pass_context
def cli(ctx: click.Context, data_path: Path | None) -> None:
    """Look up documented rate limits of public APIs, and plan around them."""
    ctx.obj = Context(data_path)


@cli.command(name="list")
@click.pass_obj
def list_apis(app: Context) -> None:
    """List the APIs in the dataset with their row counts."""
    for name, count in apis(app.data).items():
        click.echo(f"{name:<16}{count} limit{'' if count == 1 else 's'}")


@cli.command()
@click.argument("api")
@click.argument("endpoint", required=False)
@click.option("--notes", is_flag=True, help="Show source, verification date and notes.")
@click.pass_obj
def get(app: Context, api: str, endpoint: str | None, notes: bool) -> None:
    """Show the limits for API, optionally for one ENDPOINT path.

    ENDPOINT may be a real path such as /repos/octocat/hello/issues; it is matched
    against templates like /repos/{owner}/{repo}/issues. Without an endpoint, every
    row for the API is shown.
    """
    if endpoint is None:
        rows = [item for item in app.data if item.api == api.strip().lower()]
    else:
        rows = find_limits(api, endpoint, app.data, broader=True)
    if not rows:
        known = ", ".join(apis(app.data)) or "none"
        where = f"{api} {normalise_path(endpoint)}" if endpoint else api
        click.echo(f"Not found: {where}. APIs in the dataset: {known}", err=True)
        sys.exit(1)
    for item in rows:
        click.echo(_line(item))
        if notes:
            click.echo(f"    source:   {item.source}")
            click.echo(f"    verified: {item.verified}")
            if item.notes:
                click.echo(f"    notes:    {item.notes}")


@cli.command(name="search")
@click.argument("query", nargs=-1, required=True)
@click.pass_obj
def search_cmd(app: Context, query: tuple[str, ...]) -> None:
    """Find rows mentioning every word in QUERY."""
    hits = search(" ".join(query), app.data)
    if not hits:
        click.echo("No matches.", err=True)
        sys.exit(1)
    for item in hits:
        click.echo(f"{item.api:<12}{_line(item)}")


@cli.command()
@click.argument("api")
@click.argument("endpoint")
@click.option(
    "-n",
    "--requests",
    type=click.IntRange(min=1),
    required=True,
    help="How many requests you need to make.",
)
@click.option("--scope", help="Only situations whose scope contains this text.")
@click.pass_obj
def plan(app: Context, api: str, endpoint: str, requests: int, scope: str | None) -> None:
    """Estimate the fastest way to send REQUESTS requests without being throttled.

    Rows with the same scope (say an hourly and a daily cap on one key) apply together
    and the slowest decides. Rows with different scopes are alternatives, such as an
    authenticated user versus an anonymous IP, so each gets its own estimate. Assumes
    fixed windows; real services may count differently.
    """
    rows = find_limits(api, endpoint, app.data)
    if scope:
        rows = [r for r in rows if scope.lower() in r.scope.lower()]
    if not rows:
        click.echo(f"Not found: {api} {normalise_path(endpoint)}", err=True)
        sys.exit(1)
    click.echo(f"{requests} requests to {api} {normalise_path(endpoint)}")
    for name, group in group_by_scope(rows).items():
        result = make_plan(group, requests)
        click.echo("")
        click.echo(name or "default")
        for w in result.windows:
            mark = "  <- decides" if w.limit is result.binding else ""
            need = format_duration(w.seconds)
            click.echo(f"  {w.limit.allowance:<14} needs at least {need}{mark}")
        click.echo(
            f"  fastest: {format_duration(result.seconds)}; steady pace: one request "
            f"every {result.spacing_seconds:.3g}s"
        )


@cli.command()
@click.option("--format", "fmt", type=click.Choice(FORMATS), default="csv", show_default=True)
@click.option("--api", "api_filter", help="Only this API.")
@click.pass_obj
def export(app: Context, fmt: str, api_filter: str | None) -> None:
    """Write the dataset to stdout as CSV, JSON or a Markdown table."""
    rows = app.data
    if api_filter:
        rows = [r for r in rows if r.api == api_filter.strip().lower()]
        if not rows:
            click.echo(f"Not found: {api_filter}", err=True)
            sys.exit(1)
    click.echo(render(rows, fmt), nl=False)


@cli.command()
@click.argument("path", type=click.Path(path_type=Path, dir_okay=False))
def validate(path: Path) -> None:
    """Check a rate-limit CSV and report the first problem, if any."""
    rows = load_rate_limits(path)
    click.echo(f"{path}: {len(rows)} rows OK, {len({r.api for r in rows})} APIs")


if __name__ == "__main__":
    cli()
