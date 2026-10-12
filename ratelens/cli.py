"""Command line interface for ratelens."""

import click


@click.group()
def cli() -> None:
    """ratelens: look up public API rate limits."""
    pass


# Commands are registered here as they are implemented.