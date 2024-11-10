from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Body, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from gouge.colourcli import Simple
from gouge.preformatters import uvicorn_access
from langchain_postgres import PGVector

from juudge.assistant import create_chain, query
from juudge.data import load_atomic, load_core_rules
from juudge.web.dependencies import get_settings, get_store, valid_token
from juudge.web.model import BasicCredentials, QueryResponse
from juudge.web.settings import Settings


class LogFormatter(Simple):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, show_exc=True, **kwargs)
        self.pre_formatters["uvicorn.access"] = [uvicorn_access]


def create_app():

    app = FastAPI(
        title="Juudge",
        description="A web API to query Magic: The Gathering rules",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    async def redirect_to_docs():
        return RedirectResponse(url="/docs")

    @app.post("/token")
    async def get_token(
        credentials: BasicCredentials,
        settings: Settings = Depends(get_settings),
    ):
        if (
            credentials.username != settings.username
            or credentials.password != settings.password
        ):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        payload = {"sub": credentials.username}
        token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
        return token

    @app.post("/upload/atomic")
    async def upload_atomic(
        file: UploadFile = File(...),
        store: PGVector = Depends(get_store),
        token: dict[str, str] = Depends(valid_token),
    ):
        """
        Upload an MTGJson "Atomic" file to the database.
        """
        if file.filename is None:
            return JSONResponse(
                content={"status": "error", "message": "Missing filename"}
            )
        load_atomic(store, Path(file.filename))
        return JSONResponse(content={"status": "ok"})

    @app.post("/upload/rules")
    async def upload_rules(
        file: UploadFile = File(...),
        store: PGVector = Depends(get_store),
        token: dict[str, str] = Depends(valid_token),
    ):
        "Upload a core rules file to the database."
        if file.filename is None:
            return JSONResponse(
                content={"status": "error", "message": "Missing filename"}
            )
        load_core_rules(store, Path(file.filename))
        return JSONResponse(content={"status": "ok"})

    @app.post("/query")
    async def query_endpoint(
        question: Annotated[str, Body(media_type="text/plain")],
        store: PGVector = Depends(get_store),
        token: dict[str, str] = Depends(valid_token),
    ) -> QueryResponse:
        """
        Send a question to the assistant and get a response.

        The question should be a plain string.
        """
        chain = create_chain(store)
        response = query(chain, question)
        return QueryResponse.from_langchain_response(question, response)

    return app
