"""
Utility functions to connect and wire up the components of the Juudge system.
"""

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector


def create_store(database_dsn: str) -> PGVector:
    """
    Create a store for MTG cards using OpenAI embeddings and Postgres.

    :param database_dsn: The DSN for the Postgres database.
    :return: A PGVector store for MTG cards.
    """
    return PGVector(
        embeddings=OpenAIEmbeddings(),
        collection_name="mtg-cards",
        connection=database_dsn,
        use_jsonb=True,
    )
