from typing import Set
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RTL_EXP_")
    port: int = 9100
    metric_basename: str = "rtl433_weather_probe"
    allowed_ids: Set[int] = set()
