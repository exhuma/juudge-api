from typing import Any

from pydantic import BaseModel, Field

from juudge.model import MyMetadata


class DocumentMetadata(BaseModel):
    name: str = Field(description="The card name (if applicable)")
    type: str = Field(
        description="The type of docuemnt that contained the information"
    )
    identifiers: dict[str, Any] = Field(
        description=(
            "A dictionary of additional identifiers for the document. These "
            "can be used to look up the document in external systems."
        )
    )

    @staticmethod
    def from_app_metadata(metadata: MyMetadata):
        return DocumentMetadata(
            name=metadata.get("name", ""),
            type=metadata["type"],
            identifiers=dict(metadata.get("identifiers", {}) or {}),
        )


class ContextInfo(BaseModel):
    metadata: DocumentMetadata = Field(
        description="Metadata about the document"
    )
    raw_content: str = Field(
        description=(
            "The raw content of the document. This contains the data as it was "
            "used by the assistant. It may contain content that is not part of "
            "the original text. The original unmodified text is available in "
            "the metadata."
        )
    )


class QueryResponse(BaseModel):
    question: str = Field(description="The question that was submitted")
    answer: str = Field(description="The answer to the question")
    contexts: list[ContextInfo] = Field(
        description=(
            "Additional context-information that was used to construct "
            "the answer"
        )
    )

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
