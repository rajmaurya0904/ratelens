# RateLens

**Curated dataset of public API rate limits (requests per minute, burst) in CSV/JSON form, helping developers avoid throttling surprises.**

Developers integrating multiple APIs often face unexpected throttling, leading to failed requests and disrupted workflows. Keeping track of varying rate limits across services is error-prone and time-consuming. RateLens provides a centralized, up-to-date dataset to help developers avoid throttling.

## Example

<!-- A real command and its REAL pasted output. Run it first. -->

## Install

```bash
pip install -e ".[dev]"
```

## Usage

<!-- The 2-4 commands people actually need, one line each. -->

## How it works

RateLens loads a CSV file that lists public API rate limits, parses each row into a `RateLimit` object, and exposes a lookup function that searches the data by API name and endpoint, returning the matching `RateLimit` or `None` if no match is found.

## Limitations

<!-- Honest and short: what it does NOT do, known gaps. -->

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```

## License

MIT -- see [LICENSE](LICENSE).
