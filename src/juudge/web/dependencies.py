from typing import Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from langchain_postgres import PGVector

from juudge.plumbing import create_store
from juudge.web.settings import Settings


def get_settings() -> Settings:
    return Settings()


def get_store(settings: Settings = Depends(get_settings)) -> PGVector:
    store = create_store(settings.dsn)
    return store


def valid_token(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    token = credentials.credentials

    try:
        identity = jwt.decode(
            token, key=settings.secret_key, algorithms=["HS256"]
        )
        if identity["sub"] != settings.username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return identity
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
