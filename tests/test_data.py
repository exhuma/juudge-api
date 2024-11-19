from pathlib import Path
from unittest.mock import Mock

from langchain_postgres import PGVector

from juudge.data import load_atomic, load_core_rules, split_atomic, split_rules

HERE = Path(__file__).parent


def test_split_atomic():
    test_file = HERE / "data" / "atomic.json"
    with test_file.open("rb") as file:
        documents = list(split_atomic(file, file.name))
    assert len(documents) == 2
    assert documents[0].page_content == "Counter target spell."
    assert documents[1].page_content == (
        "Counter target noncreature spell. Its controller loses 2 life.\n\n"
        "Rulings:\n"
        "2018-12-07: Test ruling."
    )


def test_load_atomic():
    test_file = HERE / "data" / "atomic.json"
    store = Mock(spec=PGVector)
    with test_file.open("rb") as file:
        load_atomic(store, file, file.name)
    assert store.add_documents.call_count == 1


def test_split_rules():
    test_file = HERE / "data" / "rules.txt"
    with test_file.open("rb") as file:
        documents = list(split_rules(file, file.name))
    assert len(documents) == 40
    assert (
        documents[0].page_content == "Magic: The Gathering Comprehensive Rules"
    )
    assert (
        documents[1].page_content
        == "These rules are effective as of November 8, 2024."
    )
    assert documents[2].page_content == "Introduction"
    assert (
        documents[20].page_content
        == "100.1a A two-player game is a game that begins with only two players."
    )
    assert (
        documents[26].page_content
        == '"Abandon": To turn a face-up ongoing scheme card face down and put it on the bottom of its owner’s scheme deck. See rule 701.26, “Abandon.”'
    )


def test_load_core_rules():
    test_file = HERE / "data" / "rules.txt"
    store = Mock(spec=PGVector)
    with test_file.open("rb") as file:
        load_core_rules(store, file, file.name)
    assert store.add_documents.call_count == 1
