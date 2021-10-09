from typing import Dict, List, Optional

from werkzeug.exceptions import BadRequest, NotFound
from flask import Flask, make_response, request

from klausurarchiv import db


class Resource(object):
    def register_resource(self, app: Flask, path: str):
        def get_request_data(may_be_partial: bool = False) -> Dict:
            data = request.get_json()
            if data is None:
                raise BadRequest("Request body may not be empty")
            if not isinstance(data, Dict):
                raise BadRequest("Request body must be an object")
            for (attribute_name, attribute_type) in self.ATTRIBUTE_SCHEMA.items():
                if attribute_name not in data:
                    if may_be_partial:
                        continue
                    else:
                        raise BadRequest(f"Attribute \"{attribute_name}\" is missing")
                if not isinstance(data[attribute_name], attribute_type):
                    raise BadRequest(
                        f"Attribute \"{attribute_name}\" must be of type \"{attribute_type.__name__}\""
                    )
            return data

        def get_entry(entry_id) -> db.Entry:
            entry = self.get_entry(entry_id)
            if entry is None:
                raise NotFound("The requested resource does not exist")
            return entry

        @app.get(f"{path}")
        def get_all():
            return make_response({
                entry.entry_id: self.entry_to_dict(entry)
                for entry in self.all_entries()
            })

        @app.get(f"{path}/<int:entry_id>")
        def get(entry_id: int):
            entry = get_entry(entry_id)
            return make_response(self.entry_to_dict(entry))

        @app.post(f"{path}")
        def post():
            data = get_request_data()

            entry = self.post(data)

            response = make_response({"id": entry.entry_id}, 201)
            db.Archive.get_singleton().commit()
            return response

        @app.patch(f"{path}/<int:entry_id>")
        def patch(entry_id: int):
            data = get_request_data(may_be_partial=True)
            entry = get_entry(entry_id)

            self.patch(entry, data)

            response = make_response({})
            db.Archive.get_singleton().commit()
            return response

        @app.delete(f"{path}/<int:entry_id>")
        def delete(entry_id: int):
            entry = get_entry(entry_id)

            self.delete(entry)

            response = make_response({})
            db.Archive.get_singleton().commit()
            return response

    @property
    def archive(self) -> db.Archive:
        return db.Archive.get_singleton()

    ATTRIBUTE_SCHEMA = dict()

    def get_entry(self, entry_id: int) -> Optional[db.Entry]:
        raise NotImplementedError

    def all_entries(self) -> List[db.Entry]:
        raise NotImplementedError

    def entry_to_dict(self, entry: db.Entry) -> Dict:
        raise NotImplementedError

    def post(self, data: Dict) -> db.Entry:
        raise NotImplementedError

    def patch(self, entry: db.Entry, data: Dict):
        raise NotImplementedError

    def delete(self, entry: db.Entry):
        raise NotImplementedError


class Folder(Resource):
    ATTRIBUTE_SCHEMA = {
        "name": str
    }

    def get_entry(self, entry_id: int) -> Optional[db.Folder]:
        return self.archive.get_folder(entry_id)

    def all_entries(self) -> List[db.Folder]:
        return self.archive.folders

    def entry_to_dict(self, entry: db.Folder) -> Dict:
        return {
            "name": entry.name
        }

    def post(self, data: Dict) -> db.Folder:
        return self.archive.add_folder(data["name"])

    def patch(self, entry: db.Folder, data: Dict):
        if "name" in data:
            entry.name = data["name"]

    def delete(self, entry: db.Folder):
        self.archive.remove_folder(entry)


def create_app(app: Flask):
    for (resource, path) in [(Folder(), "/v1/folders")]:
        resource.register_resource(app, path)
