# Pydantic settings for the web server

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JUUDGE_")
    dsn: str = "postgresql+psycopg://langchain:langchain@database/langchain"
