from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector


def create_store(database_dsn: str) -> PGVector:
    return PGVector(
        embeddings=OpenAIEmbeddings(),
        collection_name="mtg-cards",
        connection=database_dsn,
        use_jsonb=True,
    )
