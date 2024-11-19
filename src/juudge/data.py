import json
import logging
import re
from itertools import batched
from typing import Any, BinaryIO, Generator

from langchain_core.documents import Document
from langchain_postgres import PGVector

from juudge.model import MyMetadata

P_RULING = re.compile(r"^\d+\.\d+[a-z]?\.? ")
P_SECTION = re.compile(r"^\d{,3}\. (.*?)$")
LOG = logging.getLogger(__name__)


def _process_single_card(card_data: dict[str, Any]) -> str:
    text = card_data.get("text", "").strip()
    rulings = card_data.get("rulings", [])
    # Add rulings to the text. This makes the text available
    # for the retriever to find. We can use the "original_text"
    # field to later retrieve the original text without the rulings.
    if rulings:
        text += "\n\nRulings:\n" + "\n".join(
            (f"{r['date']}: {r['text']}" for r in rulings)
        )
    return text.strip()


def split_detailed_set(
    file: BinaryIO, filename: str
) -> Generator[Document, None, None]:
    """
    Load card information from the MTGJson "detailed" file format.
    """
    data = json.load(file)
    items = data["data"]["cards"]
    num_items = len(items)
    for i, card_data in enumerate(items):
        text = _process_single_card(card_data)
        if not text:
            LOG.info(f"Skipping {card_data['name']} because it has no text")
            continue
        metadata: MyMetadata = {
            "name": card_data["name"],
            "identifiers": card_data["identifiers"],
            "source": filename,
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


def split_atomic(
    file: BinaryIO, filename: str
) -> Generator[Document, None, None]:
    """
    Load card information from the MTGJson "Atomic" file format.

    See https://mtgjson.com/data-models/card/card-atomic/
    Download link: https://mtgjson.com/api/v5/AtomicCards.json.gz
    """
    data = json.load(file)
    items = data["data"].items()
    num_items = len(items)
    for i, (card_name, card_data) in enumerate(items):
        for data in card_data:
            text = _process_single_card(data)
            if not text:
                LOG.info(f"Skipping {card_name} because it has no text")
                continue
            metadata: MyMetadata = {
                "name": card_name,
                "identifiers": data["identifiers"],
                "source": filename,
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


def load_atomic(store: PGVector, file: BinaryIO, filename: str):
    for batch in batched(split_atomic(file, filename), 100):
        store.add_documents(list(batch))
        LOG.debug(f"Loaded {len(batch)} documents into the database")


def load_core_rules(store: PGVector, file: BinaryIO, filename: str):
    for batch in batched(split_rules(file, filename), 100):
        store.add_documents(list(batch))
        LOG.debug(f"Loaded {len(batch)} documents into the database")


def split_rules(
    file: BinaryIO, filename: str
) -> Generator[Document, None, None]:
    state = "start"
    mtg_rules = file.read().decode("utf-8")
    for doc in mtg_rules.split("\r\n\r\n"):
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
            first_line, _, rest = doc.partition("\r\n")
            metadata: MyMetadata = {
                "source": filename,
                "type": "glossary",
                "section": state,
                "identifiers": None,
                "rulings": [],
                "name": "",
                "original_text": "",
            }
            yield Document(
                page_content=f'"{first_line}": {rest}',
                metadata=metadata,
            )
        else:
            metadata: MyMetadata = {
                "source": filename,
                "type": "other",
                "section": state,
                "name": "",
                "original_text": "",
                "identifiers": None,
                "rulings": [],
            }
            yield Document(
                page_content=doc,
                metadata=metadata,
            )
