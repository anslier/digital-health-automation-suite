from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NPRA Monitor"
    database_url: str = "sqlite:///./npra.db"
    source_url: str = (
        "https://npra.gov.my/index.php/en/informationen/"
        "new-products-indication/new-products-approved-quest3.html"
    )
    data_dir: Path = Path("/data")
    downloads_dir: Path = Path("/data/downloads")
    admin_email: str = "admin@npra.local"
    admin_password: str = "npra-demo-2026"
    session_hours: int = 12
    worker_poll_seconds: int = 5
    schedule_poll_seconds: int = 5
    browser_headless: bool = True
    download_gap_seconds: float = 1.0
    download_retries: int = 3
    import_lock_key: int = 742_404_424
    model_config = SettingsConfigDict(env_prefix="NPRA_", env_file=".env", extra="ignore")

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
