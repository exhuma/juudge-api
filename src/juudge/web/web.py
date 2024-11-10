from pathlib import Path
from typing import Annotated

from fastapi import Body, Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from langchain_postgres import PGVector

from juudge.assistant import create_chain, query
from juudge.data import load_atomic, load_core_rules
from juudge.web.dependencies import get_store
from juudge.web.model import QueryResponse


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

    @app.post("/upload/atomic")
    async def upload_atomic(
        file: UploadFile = File(...), store: PGVector = Depends(get_store)
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
        file: UploadFile = File(...), store: PGVector = Depends(get_store)
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
    ) -> QueryResponse:
        """
        Send a question to the assistant and get a response.

        The question should be a plain string.
        """
        chain = create_chain(store)
        response = query(chain, question)
        return QueryResponse.from_langchain_response(question, response)

    return app
