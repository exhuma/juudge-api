from fastapi import Depends
from langchain_postgres import PGVector

from juudge.plumbing import create_store
from juudge.web.settings import Settings


def get_settings() -> Settings:
    return Settings()


def get_store(settings: Settings = Depends(get_settings)) -> PGVector:
    store = create_store(settings.posgtresql_dsn)
    return store
