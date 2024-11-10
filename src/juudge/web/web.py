# Simple FastAPI web server for the Juudge project
# It provides API endpoints to...
#
#   - Upload a JSON file in "atomic" format
#   - Upload a text file with the Magic: The Gathering rules
#   - ask a question about a card or a rule


from pathlib import Path

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from langchain_postgres import PGVector

from juudge.assistant import create_chain, query
from juudge.data import load_atomic, load_core_rules
from juudge.web.dependencies import get_store
from juudge.web.model import QueryResponse


def create_app():

    app = FastAPI()

    @app.post("/upload/atomic")
    async def upload_atomic(
        file: UploadFile = File(...), store: PGVector = Depends(get_store)
    ):
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
        if file.filename is None:
            return JSONResponse(
                content={"status": "error", "message": "Missing filename"}
            )
        load_core_rules(store, Path(file.filename))
        return JSONResponse(content={"status": "ok"})

    @app.post("/query")
    async def query_endpoint(
        question: str, store: PGVector = Depends(get_store)
    ) -> QueryResponse:
        chain = create_chain(store)
        response = query(chain, question)
        return QueryResponse.from_langchain_response(question, response)

    return app
