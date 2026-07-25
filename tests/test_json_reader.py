"""Tests for read_cards_json in ankideck.reader."""

import json
import jsonschema
import pytest


def test_sample_file_is_schema_valid():
    with open("schemas/card.schema.json", encoding="utf-8") as f:
        schema = json.load(f)
    with open("samples/sample_vocabulary.json", encoding="utf-8") as f:
        data = json.load(f)
    jsonschema.validate(data, schema)
