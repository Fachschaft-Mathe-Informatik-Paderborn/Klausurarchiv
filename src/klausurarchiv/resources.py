from typing import Dict, List, Optional

from flask import Flask, make_response, request
from werkzeug.exceptions import BadRequest, NotFound

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

        @app.get(f"{path}", endpoint=f"GET {path}")
        def get_all():
            return make_response({
                entry.entry_id: self.entry_to_dict(entry)
                for entry in self.all_entries()
            })

        @app.get(f"{path}/<int:entry_id>", endpoint=f"GET {path}/id")
        def get(entry_id: int):
            entry = get_entry(entry_id)
            return make_response(self.entry_to_dict(entry))

        @app.post(f"{path}", endpoint=f"POST {path}")
        def post():
            data = get_request_data()

            entry = self.post(data)

            response = make_response({"id": entry.entry_id}, 201)
            db.Archive.get_singleton().commit()
            return response

        @app.patch(f"{path}/<int:entry_id>", endpoint=f"PATCH {path}/id")
        def patch(entry_id: int):
            data = get_request_data(may_be_partial=True)
            entry = get_entry(entry_id)

            self.patch(entry, data)

            response = make_response({})
            db.Archive.get_singleton().commit()
            return response

        @app.delete(f"{path}/<int:entry_id>", endpoint=f"DELETE {path}/id")
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


class Document(Resource):
    ATTRIBUTE_SCHEMA = {
        "filename": str,
        "downloadable": bool,
        "content_type": str
    }

    ALLOWED_CONTENT_TYPES = [
        "application/msword", "application/pdf", "application/x-latex", "image/png", "image/jpeg", "image/gif",
        "text/plain"
    ]

    def get_entry(self, entry_id: int) -> Optional[db.Document]:
        return self.archive.get_document(entry_id)

    def all_entries(self) -> List[db.Document]:
        return self.archive.documents

    def entry_to_dict(self, entry: db.Document) -> Dict:
        return {
            "filename": entry.filename,
            "downloadable": entry.downloadable,
            "content_type": entry.content_type
        }

    def post(self, data: Dict) -> db.Document:
        if data["content_type"] not in self.ALLOWED_CONTENT_TYPES:
            raise BadRequest("Illegal content_type")
        return self.archive.add_document(filename=data["filename"], downloadable=data["downloadable"],
                                         content_type=data["content_type"])

    def patch(self, entry: db.Document, data: Dict):
        if "filename" in data:
            entry.filename = data["filename"]
        if "downloadable" in data:
            entry.downloadable = data["downloadable"]
        if "content_type" in data:
            if data["content_type"] not in self.ALLOWED_CONTENT_TYPES:
                raise BadRequest("Illegal content type")
            entry.content_type = data["content_type"]

    def delete(self, entry: db.Document):
        self.archive.remove_document(entry)


class Course(Resource):
    ATTRIBUTE_SCHEMA = {
        "long_name": str,
        "short_name": str
    }

    def get_entry(self, entry_id: int) -> Optional[db.Course]:
        return self.archive.get_course(entry_id)

    def all_entries(self) -> List[db.Course]:
        return self.archive.courses

    def entry_to_dict(self, entry: db.Course) -> Dict:
        return {
            "long_name": entry.long_name,
            "short_name": entry.short_name
        }

    def post(self, data: Dict) -> db.Course:
        return self.archive.add_course(short_name=data["short_name"], long_name=data["long_name"])

    def patch(self, entry: db.Course, data: Dict):
        if "long_name" in data:
            entry.long_name = data["long_name"]
        if "short_name" in data:
            entry.short_name = data["short_name"]

    def delete(self, entry: db.Course):
        self.archive.remove_course(entry)


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
    for (resource, path) in [(Document(), "/v1/documents"), (Course(), "/v1/courses"), (Folder(), "/v1/folders")]:
        resource.register_resource(app, path)
