import json
import tempfile

from flask import Flask
from klausurarchiv.resources import Resource
from klausurarchiv import db
from typing import List, Optional, Dict

def test_resource():
    class TestEntry(db.Entry):
        def __init__(self, id: int, name: str, age: int, paths: List[str]):
            self.id = id
            self.name = name
            self.age = age
            self.paths = paths

        @property
        def entry_id(self) -> int:
            return self.id

    class TestResource(Resource):
        def __init__(self):
            self.entries: List[TestEntry] = list()

        ATTRIBUTE_SCHEMA = {"name": str, "age": int, "paths": List}

        @staticmethod
        def assert_types(data: Dict):
            if "name" in data:
                assert isinstance(data["name"], str)
            if "age" in data:
                assert isinstance(data["age"], int)
            if "paths" in data:
                assert isinstance(data["paths"], List)
                for path in data["paths"]:
                    assert isinstance(path, str)

        def get_entry(self, entry_id: int) -> Optional[TestEntry]:
            if entry_id < len(self.entries):
                return self.entries[entry_id]
            else:
                return None

        def all_entries(self) -> List[TestEntry]:
            return self.entries

        def entry_to_dict(self, entry: TestEntry) -> Dict:
            return {
                "name": entry.name,
                "age": entry.age,
                "paths": entry.paths
            }

        def post(self, data: Dict) -> TestEntry:
            assert "name" in data
            assert "age" in data
            assert "paths" in data
            self.assert_types(data)

            new_id = len(self.entries)
            new_entry = TestEntry(new_id, data["name"], data["age"], data["paths"])
            self.entries.append(new_entry)
            return new_entry

        def patch(self, entry: db.Entry, data: Dict):
            self.assert_types(data)

            if "name" in data:
                entry.name = data["name"]
            if "age" in data:
                entry.age = data["age"]
            if "paths" in data:
                entry.paths = data["paths"]

        def delete(self, entry: db.Entry):
            if entry.entry_id < len(self.entries):
                self.entries[entry.id] = None
