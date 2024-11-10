# Pydantic settings for the web server

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    posgtresql_dsn: str = (
        "postgresql+psycopg://langchain:langchain@database/langchain"
    )
