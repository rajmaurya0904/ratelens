import json

import pytest
from click.testing import CliRunner

from ratelens import __version__
from ratelens.cli import cli

GOOD = (
    "api,endpoint,limit,window_seconds,scope\n"
    "demo,/things/{id},10,1,per key\n"
    "demo,/things/{id},100,60,per key\n"
    "demo,/*,5,1,anon\n"
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def demo_csv(tmp_path):
    path = tmp_path / "demo.csv"
    path.write_text(GOOD)
    return str(path)


def test_help_lists_commands(runner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for name in ("list", "get", "search", "plan", "export", "validate"):
        assert name in result.output


def test_version(runner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0 and __version__ in result.output


def test_list_shows_apis(runner) -> None:
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "github" in result.output and "stripe" in result.output


def test_get_known_endpoint(runner) -> None:
    result = runner.invoke(cli, ["get", "github", "/search/code"])
    assert result.exit_code == 0
    assert "10 per minute" in result.output


def test_get_matches_template(runner) -> None:
    result = runner.invoke(cli, ["get", "airtable", "/v0/app123/Table"])
    assert result.exit_code == 0 and "5 per second" in result.output


def test_get_without_endpoint_lists_all_rows(runner) -> None:
    result = runner.invoke(cli, ["get", "openmeteo"])
    assert result.exit_code == 0
    assert result.output.count("/v1/forecast") == 3


def test_get_shows_broader_limits_too(runner) -> None:
    result = runner.invoke(cli, ["get", "stripe", "/v1/files"])
    assert "20 per second" in result.output and "100 per second" in result.output


def test_get_notes_flag(runner) -> None:
    result = runner.invoke(cli, ["get", "discord", "/channels/1", "--notes"])
    assert "source:" in result.output and "verified:" in result.output


def test_get_unknown_exits_one_and_lists_apis(runner) -> None:
    result = runner.invoke(cli, ["get", "nosuchapi", "/x"])
    assert result.exit_code == 1
    assert "Not found" in result.output and "github" in result.output


def test_get_unknown_endpoint_exits_one(runner, demo_csv) -> None:
    other = runner.invoke(cli, ["--data", demo_csv, "get", "demo", "/zzz"])
    assert other.exit_code == 0  # falls back to /*
    none = runner.invoke(cli, ["--data", demo_csv, "get", "github", "/zzz"])
    assert none.exit_code == 1


def test_search(runner) -> None:
    result = runner.invoke(cli, ["search", "telegram", "group"])
    assert result.exit_code == 0 and "20 per minute" in result.output


def test_search_no_hits(runner) -> None:
    result = runner.invoke(cli, ["search", "zzzzqqq"])
    assert result.exit_code == 1


def test_plan_reports_each_scope(runner, demo_csv) -> None:
    result = runner.invoke(cli, ["--data", demo_csv, "plan", "demo", "/things/9", "-n", "1000"])
    assert result.exit_code == 0
    assert "per key" in result.output
    assert "10 per second" in result.output and "100 per minute" in result.output
    assert "decides" in result.output
    assert "fastest: 9m" in result.output  # (1000/100 - 1) windows of 60 s


def test_plan_scope_filter(runner) -> None:
    result = runner.invoke(cli, ["plan", "github", "/user", "-n", "5001", "--scope", "unauth"])
    assert result.exit_code == 0
    assert "unauthenticated" in result.output and "authenticated user" not in result.output


def test_plan_needs_positive_count(runner) -> None:
    assert runner.invoke(cli, ["plan", "github", "/user", "-n", "0"]).exit_code == 2
    assert runner.invoke(cli, ["plan", "github", "/user"]).exit_code == 2


def test_plan_unknown_api(runner) -> None:
    assert runner.invoke(cli, ["plan", "nope", "/x", "-n", "5"]).exit_code == 1


def test_export_csv_default(runner) -> None:
    result = runner.invoke(cli, ["export"])
    assert result.exit_code == 0
    assert result.output.startswith("api,endpoint,requests_per_minute,burst,")


def test_export_json_filtered(runner) -> None:
    result = runner.invoke(cli, ["export", "--format", "json", "--api", "Stripe"])
    data = json.loads(result.output)
    assert data and {row["api"] for row in data} == {"stripe"}


def test_export_markdown(runner) -> None:
    result = runner.invoke(cli, ["export", "--format", "markdown", "--api", "slack"])
    assert result.output.startswith("| api |")


def test_export_bad_format_is_usage_error(runner) -> None:
    assert runner.invoke(cli, ["export", "--format", "xml"]).exit_code == 2


def test_export_unknown_api(runner) -> None:
    assert runner.invoke(cli, ["export", "--api", "nope"]).exit_code == 1


def test_missing_data_file_message(runner, tmp_path) -> None:
    missing = tmp_path / "gone.csv"
    result = runner.invoke(cli, ["--data", str(missing), "list"])
    assert result.exit_code == 1
    assert result.output.strip() == f"Error: Data file not found at {missing}"


def test_bad_data_file_reports_line(runner, tmp_path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("api,endpoint,limit,window_seconds\na,/x,many,1\n")
    result = runner.invoke(cli, ["--data", str(bad), "list"])
    assert result.exit_code == 1
    assert "line 2" in result.output and "whole number" in result.output


def test_validate_ok_and_failure(runner, demo_csv, tmp_path) -> None:
    ok = runner.invoke(cli, ["validate", demo_csv])
    assert ok.exit_code == 0 and "3 rows OK" in ok.output
    bad = tmp_path / "bad.csv"
    bad.write_text("api,endpoint,limit,window_seconds\na,x,1,1\n")
    assert runner.invoke(cli, ["validate", str(bad)]).exit_code == 1


def test_validate_bundled_dataset(runner) -> None:
    from ratelens.loader import default_data_path

    result = runner.invoke(cli, ["validate", str(default_data_path())])
    assert result.exit_code == 0
