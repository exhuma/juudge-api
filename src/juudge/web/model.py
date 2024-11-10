from typing import Any

from pydantic import BaseModel

from juudge.model import MyMetadata


class DocumentMetadata(BaseModel):
    name: str
    type: str
    identifiers: dict[str, Any]

    @staticmethod
    def from_app_metadata(metadata: MyMetadata):
        return DocumentMetadata(
            name=metadata["name"],
            type=metadata["type"],
            identifiers=dict(metadata["identifiers"] or {}),
        )


class ContextInfo(BaseModel):
    metadata: DocumentMetadata
    raw_content: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    contexts: list[ContextInfo]

    @staticmethod
    def from_langchain_response(
        original_question: str, response: dict[str, Any]
    ):
        return QueryResponse(
            question=original_question,
            answer=response["answer"],
            contexts=[
                ContextInfo(
                    metadata=DocumentMetadata.from_app_metadata(ctx.metadata),
                    raw_content=ctx.page_content,
                )
                for ctx in response["context"]
            ],
        )
