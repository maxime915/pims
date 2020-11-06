import json

import pytest

from pims.formats.metadata import Metadata, MetadataType, MetadataStore, boolean_parser, json_parser


def test_boolean_parser():
    assert boolean_parser(True) is True
    assert boolean_parser(False) is False
    assert boolean_parser("truE") is True
    assert boolean_parser("YeS") is True
    assert boolean_parser("nO") is False

    with pytest.raises(ValueError):
        boolean_parser("test")


def test_json_parser():
    assert json_parser("{}") == dict()
    assert json_parser('{ "age":100}') == dict(age=100)
    assert json_parser("{\"age\":100 }") == dict(age=100)
    assert json_parser('{"age":100 }') == dict(age=100)
    assert json_parser('{"foo":[5,6.8],"foo":"bar"}') == dict(foo="bar")

    with pytest.raises(ValueError):
        json_parser("{asdf}")

    with pytest.raises(ValueError):
        json_parser("{'age':100 }")


def test_metadatatype():
    assert MetadataType.STRING.name == "STRING"
    assert MetadataType.INTEGER.name == "INTEGER"
    assert MetadataType.BOOLEAN.name == "BOOLEAN"
    assert MetadataType.DECIMAL.name == "DECIMAL"
    assert MetadataType.JSON.name == "JSON"


def test_metadata():
    data = [
        ("b", MetadataType.STRING, "b"),
        ("2", MetadataType.INTEGER, 2),
        ("2.2", MetadataType.DECIMAL, 2.2),
        ("True", MetadataType.BOOLEAN, True),
        ("true", MetadataType.BOOLEAN, True),
        ('{"a":2}', MetadataType.JSON, json.loads('{"a":2}'))
    ]

    for item in data:
        value, dtype, parsed_value = item
        m = Metadata("test", value, dtype)
        assert m.name == "test"
        assert m.raw_value == value
        assert m.dtype == dtype
        assert m.parsed_value == parsed_value

        m = Metadata("test", value)
        assert m.name == "test"
        assert m.raw_value == value
        assert m.dtype == dtype
        assert m.parsed_value == parsed_value


def test_metadatastore():
    ms = MetadataStore()
    assert len(ms) == 0

    ms.set("a", "b", MetadataType.STRING)
    assert len(ms) == 1
    assert ms["a"] == Metadata("a", "b", MetadataType.STRING)
    assert ms.get("a") == Metadata("a", "b", MetadataType.STRING)
    assert ms.get_value("a") == "b"
    assert ms.get_dtype("a") == MetadataType.STRING

    ms.set("a", "2")
    assert len(ms) == 1
    assert ms.get("a") == Metadata("a", "2", MetadataType.INTEGER)
    assert ms.get("a") == Metadata("a", "2")
    assert ms.get_value("a") == 2
    assert ms.get_value("a", parsed=False) == "2"
