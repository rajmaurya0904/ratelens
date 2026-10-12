"""Command line interface for ratelens."""

import click

from .loader import load_rate_limits
from .lookup import get_rate_limit


@click.group()
def cli() -> None:
    """ratelens: look up public API rate limits."""
    pass


@cli.command()
@click.argument('api')
@click.argument('endpoint')
def get(api: str, endpoint: str) -> None:
    """Print rate limit for API and endpoint."""
    data = load_rate_limits("ratelens/data/sample_rate_limits.csv")
    limit = get_rate_limit(api, endpoint, data)
    if limit is None:
        print("Not found")
    else:
        print(f"{limit.requests_per_minute} {limit.burst}")