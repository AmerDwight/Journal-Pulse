from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    project_name: str = 'journal-pulse'
    data_root: Path = Path('/home/amer-test/journal-pulse/data')

    minio_endpoint: str = 'localhost:9000'
    minio_access_key: str = 'minioadmin'
    minio_secret_key: str = 'minioadmin'
    minio_secure: bool = False

    raw_bucket: str = Field(default='journal-raw', alias='minio_raw_bucket')
    report_bucket: str = Field(default='journal-reports', alias='minio_report_bucket')

    daily_report_hour: int = 8
    daily_report_minute: int = 0

    discord_bot_token: str = ''
    discord_channel_id: str = ''
    discord_enable_message_content_intent: bool = True

    llm_backend: str = 'openrouter'
    llm_provider_order: str = 'openrouter'
    llm_api_base_url: str = 'https://openrouter.ai/api/v1'
    llm_api_key: str = ''
    llm_model: str = 'nvidia/nemotron-3-super-120b-a12b:free'
    llm_timeout_seconds: float = 30.0
    llm_extra_headers_json: str = '{}'
