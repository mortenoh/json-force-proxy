"""Tests for the CLI."""

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from json_force_proxy.cli import app
from json_force_proxy.settings import get_settings

runner = CliRunner()


@pytest.fixture(autouse=True)
def clean_environment() -> Generator[None, None, None]:
    """Clean up environment variables after each test."""
    yield
    # Remove any env vars set during tests
    for key in list(os.environ.keys()):
        if key.startswith("JSON_FORCE_PROXY_"):
            del os.environ[key]
    get_settings.cache_clear()


class TestCLITargetOption:
    """Tests for CLI --target option being passed to server."""

    def test_target_option_sets_environment_variable(self) -> None:
        """Test that --target option sets JSON_FORCE_PROXY_TARGET_URL env var."""
        with patch("json_force_proxy.cli.uvicorn.run") as mock_uvicorn:
            # Clear any cached settings
            get_settings.cache_clear()

            runner.invoke(app, ["--target", "https://example.com/api"])

            # Verify environment variable was set
            assert os.environ.get("JSON_FORCE_PROXY_TARGET_URL") == "https://example.com/api"

            # Verify uvicorn was called
            mock_uvicorn.assert_called_once()

    def test_target_option_displayed_in_output(self) -> None:
        """Test that --target option is displayed in startup output."""
        with patch("json_force_proxy.cli.uvicorn.run"):
            get_settings.cache_clear()

            result = runner.invoke(app, ["--target", "https://example.com/api"])

            assert "Proxying: https://example.com/api" in result.output

    def test_error_when_target_not_specified(self) -> None:
        """Test that error is shown when --target is not specified."""
        # Clear the env var if set from previous test
        os.environ.pop("JSON_FORCE_PROXY_TARGET_URL", None)

        with patch("json_force_proxy.cli.uvicorn.run"):
            get_settings.cache_clear()

            result = runner.invoke(app, [])

            assert result.exit_code == 1
            assert "Error: --target is required" in result.output


class TestCLIPortOption:
    """Tests for CLI --port option."""

    def test_port_option_passed_to_uvicorn(self) -> None:
        """Test that --port option is passed to uvicorn."""
        with patch("json_force_proxy.cli.uvicorn.run") as mock_uvicorn:
            get_settings.cache_clear()

            runner.invoke(app, ["--target", "https://example.com", "--port", "9000"])

            mock_uvicorn.assert_called_once()
            call_kwargs = mock_uvicorn.call_args[1]
            assert call_kwargs["port"] == 9000

    def test_port_displayed_in_output(self) -> None:
        """Test that port is displayed in startup output."""
        with patch("json_force_proxy.cli.uvicorn.run"):
            get_settings.cache_clear()

            result = runner.invoke(app, ["--target", "https://example.com", "--port", "9000"])

            assert "http://0.0.0.0:9000" in result.output


class TestCLIHostOption:
    """Tests for CLI --host option."""

    def test_host_option_passed_to_uvicorn(self) -> None:
        """Test that --host option is passed to uvicorn."""
        with patch("json_force_proxy.cli.uvicorn.run") as mock_uvicorn:
            get_settings.cache_clear()

            runner.invoke(app, ["--target", "https://example.com", "--host", "127.0.0.1"])

            mock_uvicorn.assert_called_once()
            call_kwargs = mock_uvicorn.call_args[1]
            assert call_kwargs["host"] == "127.0.0.1"


class TestCLILogLevelOption:
    """Tests for CLI --log-level option."""

    def test_log_level_option_passed_to_uvicorn(self) -> None:
        """Test that --log-level option is passed to uvicorn."""
        with patch("json_force_proxy.cli.uvicorn.run") as mock_uvicorn:
            get_settings.cache_clear()

            runner.invoke(app, ["--target", "https://example.com", "--log-level", "DEBUG"])

            mock_uvicorn.assert_called_once()
            call_kwargs = mock_uvicorn.call_args[1]
            assert call_kwargs["log_level"] == "debug"

    def test_log_level_displayed_in_output(self) -> None:
        """Test that log level is displayed in startup output."""
        with patch("json_force_proxy.cli.uvicorn.run"):
            get_settings.cache_clear()

            result = runner.invoke(app, ["--target", "https://example.com", "--log-level", "DEBUG"])

            assert "Log level: DEBUG" in result.output


class TestCLICombinedOptions:
    """Tests for combining multiple CLI options."""

    def test_all_options_together(self) -> None:
        """Test that all CLI options work together."""
        with patch("json_force_proxy.cli.uvicorn.run") as mock_uvicorn:
            get_settings.cache_clear()

            result = runner.invoke(
                app,
                [
                    "--target",
                    "https://api.example.com",
                    "--port",
                    "3000",
                    "--host",
                    "127.0.0.1",
                    "--log-level",
                    "WARNING",
                ],
            )

            assert result.exit_code == 0
            assert "Proxying: https://api.example.com" in result.output
            assert "http://127.0.0.1:3000" in result.output
            assert "Log level: WARNING" in result.output

            call_kwargs = mock_uvicorn.call_args[1]
            assert call_kwargs["host"] == "127.0.0.1"
            assert call_kwargs["port"] == 3000
            assert call_kwargs["log_level"] == "warning"
