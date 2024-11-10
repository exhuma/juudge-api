from typing import Literal, TypedDict


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
    type: Literal["core-rule", "card-text", "glossary", "other"]
    section: str
