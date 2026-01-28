import aden_tools.credentials.cli as cli
from aden_tools.credentials.base import CredentialManager, CredentialSpec

CUSTOM_SPECS = {
    "anthropic": CredentialSpec(
        env_var="ANTHROPIC_API_KEY",
        tools=[],
        node_types=["llm_generate", "llm_tool_use"],
        required=True,
        startup_required=True,
        help_url="https://console.anthropic.com/settings/keys",
        description="API key for Anthropic Claude models",
    )
}


def test_cli_check_node_types_missing_key(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def _cm():
        return CredentialManager(specs=CUSTOM_SPECS, dotenv_path=tmp_path / ".env")

    monkeypatch.setattr(cli, "CredentialManager", _cm)

    code = cli.main(["check", "--node-types", "llm_generate,llm_tool_use"])
    out = capsys.readouterr().out

    assert code == 1
    assert "Missing required credentials" in out
    assert "ANTHROPIC_API_KEY" in out


def test_cli_check_startup_missing_key(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    def _cm():
        return CredentialManager(specs=CUSTOM_SPECS, dotenv_path=tmp_path / ".env")

    monkeypatch.setattr(cli, "CredentialManager", _cm)

    code = cli.main(["check", "--startup"])
    out = capsys.readouterr().out

    assert code == 1
    assert "Server startup failed" in out
    assert "ANTHROPIC_API_KEY" in out


def test_cli_check_ok_when_key_present(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def _cm():
        return CredentialManager(specs=CUSTOM_SPECS, dotenv_path=tmp_path / ".env")

    monkeypatch.setattr(cli, "CredentialManager", _cm)

    code = cli.main(["check", "--node-types", "llm_generate,llm_tool_use"])
    out = capsys.readouterr().out

    assert code == 0
    assert "All required credentials are present" in out
