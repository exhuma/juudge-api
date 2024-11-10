import json
import logging
import re
from itertools import batched
from os import environ
from textwrap import wrap
from typing import Generator, Literal, TypedDict

import dotenv
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector

P_RULING = re.compile(r"^\d+\.\d+[a-z]?\.? ")
P_SECTION = re.compile(r"^\d{,3}\. (.*?)$")
LOG = logging.getLogger(__name__)


class Ruling(TypedDict):
    date: str
    text: str


class Identifiers(TypedDict):
    name: str


class MyMetadata(TypedDict):
    name: str
    original_text: str
    identifiers: Identifiers | None
    source: str
    rulings: list[Ruling]
    type: Literal["core-rule", "card-text"]
    section: str


def load_atomic(file_path: str) -> Generator[Document, None, None]:
    """
    Load card information from the MTGJson "Atomic" file format.

    See https://mtgjson.com/data-models/card/card-atomic/
    Download link: https://mtgjson.com/api/v5/AtomicCards.json.gz
    """
    with open(file_path) as f:
        data = json.load(f)
        items = data["data"].items()
        num_items = len(items)
        for i, (card_name, card_data) in enumerate(items):
            for data in card_data:
                text = data.get("text", "")
                rulings = data.get("rulings", [])
                if not text:
                    LOG.info(f"Skipping {card_name} because it has no text")
                    continue
                # Add rulings to the text. This makes the text available
                # for the retriever to find. We can use the "original_text"
                # field to later retrieve the original text without the rulings.
                if rulings:
                    text += "\n\nRulings:\n" + "\n".join(
                        (f"{r['date']}: {r['text']}" for r in data["rulings"])
                    )
                metadata: MyMetadata = {
                    "name": card_name,
                    "identifiers": data["identifiers"],
                    "source": "data/atomic.json",
                    "original_text": text,
                    "rulings": data.get("rulings", []),
                    "type": "card-text",
                    "section": "",
                }
                doc = Document(
                    page_content=text,
                    metadata=metadata,
                )
                LOG.debug(f"Loaded {i+1}/{num_items} cards")
                yield doc


def load_core_rules(store: PGVector):
    for batch in batched(split_rules("data/MagicCompRules 20241108.txt"), 100):
        store.add_documents(list(batch))
        LOG.debug(f"Loaded {len(batch)} documents into the database")


def split_rules(filename: str) -> Generator[Document, None, None]:
    # This is a long document we can split up.
    state = "start"
    with open(filename) as f:
        mtg_rules = f.read()
        for doc in mtg_rules.split("\n\n"):
            doc = doc.strip()
            if doc == "":
                continue
            section_match = P_SECTION.match(doc)
            if section_match:
                state = section_match.group(1)
            elif doc == "Glossary":
                state = "Glossary"
            elif doc == "Credits":
                state = "end"
            if P_RULING.match(doc):
                metadata: MyMetadata = {
                    "source": filename,
                    "type": "core-rule",
                    "section": state,
                    "name": "",
                    "original_text": doc,
                    "identifiers": None,
                    "rulings": [],
                }

                yield Document(
                    page_content=doc,
                    metadata=metadata,
                )
            elif state == "Glossary":
                first_line, _, rest = doc.partition("\n")
                yield Document(
                    page_content=f'"{first_line}": {rest}',
                    metadata={
                        "source": filename,
                        "type": "glossary",
                        "section": state,
                    },
                )
            else:
                yield Document(
                    page_content=doc,
                    metadata={
                        "source": filename,
                        "type": "other",
                        "section": state,
                    },
                )


def main():
    dotenv.load_dotenv()
    llm = ChatOpenAI(model="gpt-4")
    vectorstore = PGVector(
        embeddings=OpenAIEmbeddings(),
        collection_name="mtg-cards",
        connection="postgresql+psycopg://langchain:langchain@database/langchain",
        use_jsonb=True,
    )
    retriever = vectorstore.as_retriever()

    if "LOAD" in environ:
        LOG.debug("loading")
        for batch in batched(load_atomic("./data/atomic.json"), 100):
            vectorstore.add_documents(list(batch))
            LOG.debug(f"Loaded {len(batch)} documents into the database")
        load_core_rules(vectorstore)
        LOG.debug("done loading")

    # Incorporate the retriever into a question-answering chain.
    system_prompt = (
        'you are an expert in "magic: the gathering" and you are asked to answer a '
        "question about the game. Your answers are consise an take extra care "
        "about rulings of the cards. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know."
        # "Use three sentences maximum and keep the "
        # "answer concise."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    question = "When playing the card 'Another Round' and a card has an ETB efferct, does the ETB effect trigger?"
    response = rag_chain.invoke({"input": question})

    print("=== Question ===")
    wrapped = wrap(question, 80)
    for line in wrapped:
        print(line)
    print("=== Answer ===")
    wrapped = wrap(response["answer"], 80)
    for line in wrapped:
        print(line)
    print("=== Context ===")
    for ctx in response["context"]:
        if "name" in ctx.metadata:
            print(f"Card:   {ctx.metadata['name']}")
            for id_name, value in ctx.metadata.get("identifiers", {}).items():
                if id_name == "scryfallOracleId":
                    # Print URL
                    print(
                        f"URL:    https://tagger.scryfall.com/card/oracle/{
                            value}"
                    )
                else:
                    print(f"{id_name}: {value}")
            print(f"IDs:    {ctx.metadata.get('identifiers', '')}")
            print(ctx.page_content)
        elif ctx.metadata.get("type", None) == "core-rule":
            print("Core Rule")
            wrapped = wrap(ctx.page_content, 80)
            for line in wrapped:
                print(line)
        else:
            print(ctx)
        print("---------------")


if __name__ == "__main__":
    main()
