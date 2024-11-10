import json
import logging
import re
from itertools import batched
from pathlib import Path
from typing import Generator

from langchain_core.documents import Document
from langchain_postgres import PGVector

from juudge.model import MyMetadata

P_RULING = re.compile(r"^\d+\.\d+[a-z]?\.? ")
P_SECTION = re.compile(r"^\d{,3}\. (.*?)$")
LOG = logging.getLogger(__name__)


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


def load_core_rules(store: PGVector, filename: Path):
    for batch in batched(split_rules(filename), 100):
        store.add_documents(list(batch))
        LOG.debug(f"Loaded {len(batch)} documents into the database")


def split_rules(filename: Path) -> Generator[Document, None, None]:
    # This is a long document we can split up.
    state = "start"
    with filename.open() as f:
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
                    "source": str(filename),
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
                metadata: MyMetadata = {
                    "source": str(filename),
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
                    "source": str(filename),
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


def load_all(vectorstore: PGVector):
    LOG.debug("loading")
    for batch in batched(load_atomic("./data/atomic.json"), 100):
        vectorstore.add_documents(list(batch))
        LOG.debug(f"Loaded {len(batch)} documents into the database")
    load_core_rules(vectorstore, Path("data/MagicCompRules 20241108.txt"))
    LOG.debug("done loading")
