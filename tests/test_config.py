from pathlib import Path

from journal_pulse.config import Settings
from journal_pulse.sources.defaults import build_default_sources


def test_settings_builds_default_paths(tmp_path):
    settings = Settings(
        project_name="demo-project",
        minio_endpoint="localhost:9000",
        minio_access_key="minioadmin",
        minio_secret_key="minioadmin",
        data_root=tmp_path,
    )

    assert settings.raw_bucket == "journal-raw"
    assert settings.report_bucket == "journal-reports"
    assert settings.data_root == tmp_path


def test_settings_include_discord_delivery_configuration():
    settings = Settings(discord_bot_token="bot-token", discord_channel_id="1234567890")

    assert settings.discord_bot_token == "bot-token"
    assert settings.discord_channel_id == "1234567890"
    assert settings.discord_enable_message_content_intent is True


def test_default_sources_include_mainstream_journals():
    names = {source.name for source in build_default_sources()}
    assert {"nature", "science", "cell"}.issubset(names)


def test_env_example_has_valid_key_value_lines():
    env_example = Path(__file__).resolve().parent.parent / ".env.example"

    lines = env_example.read_text(encoding="utf-8").splitlines()

    assert all("=" in line for line in lines)
    assert 'DISCORD_BOT_TOKEN=***' in lines
    assert 'DISCORD_CHANNEL_ID=' in lines


def test_gitignore_excludes_sensitive_and_generated_files():
    gitignore = Path(__file__).resolve().parent.parent / ".gitignore"

    content = gitignore.read_text(encoding="utf-8")

    assert ".env" in content
    assert "data/" in content
    assert "__pycache__/" in content
