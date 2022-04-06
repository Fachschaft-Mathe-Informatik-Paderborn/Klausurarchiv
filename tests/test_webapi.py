from functools import wraps
from hashlib import sha256
from typing import Callable, Dict

import pytest
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from klausurarchiv import create_app


@pytest.fixture
def client() -> FlaskClient:
    password_hash = sha256(bytes("4711", encoding="utf-8")).hexdigest()
    app = create_app(
        {"TESTING": True, "USERNAME": "john", "PASSWORD_SHA256": password_hash})

    with app.test_client() as client:
        yield client


def login(client: FlaskClient, username: str = "john", password: str = "4711"):
    return client.post("/v1/login", json={
        "username": username,
        "password": password
    })


def logout(client: FlaskClient):
    return client.post("/v1/logout")


def authenticated(function: Callable):
    @wraps(function)
    def wrapper(client: FlaskClient, *args, **kwargs):
        login(client)
        result = function(client, *args, **kwargs)
        logout(client)
        return result

    return wrapper


def test_login_logout(client: FlaskClient):
    # Logging out with being logged in
    response: TestResponse = logout(client)
    assert response.status_code == 200
    assert response.get_json() == {}

    # Making an unauthorized request
    response: TestResponse = client.post("/v1/folders", json={
        "name": "Folder1"
    })
    assert response.status_code == 401

    # Logging in
    response: TestResponse = login(client)
    assert response.status_code == 200
    assert response.get_json() == {}

    # Making an authorized request
    response: TestResponse = client.post("/v1/folders", json={
        "name": "Folder1"
    })
    assert response.status_code == 201

    # Logging in again, should not change state
    response: TestResponse = login(client)
    assert response.status_code == 200
    assert response.get_json() == {}

    # Making another unauthorized request
    response: TestResponse = client.post("/v1/folders", json={
        "name": "Folder1"
    })
    assert response.status_code == 201

    # Logging out
    response: TestResponse = logout(client)
    assert response.status_code == 200
    assert response.get_json() == {}

    # Making an unauthorized request
    response: TestResponse = client.post("/v1/folders", json={
        "name": "Folder1"
    })
    assert response.status_code == 401

    # Trying to log in with invalid credentials
    response: TestResponse = client.post("/v1/login", json={
        "username": "jane",
        "password": "1612"
    })
    assert response.status_code == 401

    # Making an unauthorized request
    response: TestResponse = client.post("/v1/folders", json={
        "name": "Folder1"
    })
    assert response.status_code == 401


def template_test_resource(client: FlaskClient, resource_name: str, initial_data: Dict, partial_patch: Dict,
                           full_patch: Dict):
    # Checking the initial state
    response: TestResponse = client.get(f"/v1/{resource_name}")
    assert response.status_code == 200
    assert response.get_json() == {}

    # Creating a new folder
    response: TestResponse = client.post(f"/v1/{resource_name}", json=initial_data)
    assert response.status_code == 201
    rs_id = response.get_json()["id"]
    assert isinstance(rs_id, int)

    # Checking with the new folder was created
    response: TestResponse = client.get(f"/v1/{resource_name}")
    assert response.status_code == 200
    assert response.get_json() == {str(rs_id): initial_data}

    # Checking whether the individual query works
    response: TestResponse = client.get(f"/v1/{resource_name}/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == initial_data

    # Partial Patching
    response: TestResponse = client.patch(f"/v1/{resource_name}/{rs_id}", json=partial_patch)
    assert response.status_code == 200
    assert response.get_json() == {}

    patched_data = initial_data
    for (key, value) in partial_patch.items():
        patched_data[key] = value

    # Checking that partial patches were applied
    response: TestResponse = client.get(f"/v1/{resource_name}")
    assert response.status_code == 200
    assert response.get_json() == {str(rs_id): patched_data}

    response: TestResponse = client.get(f"/v1/{resource_name}/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == patched_data

    # Full Patching
    response: TestResponse = client.patch(f"/v1/{resource_name}/{rs_id}", json=full_patch)
    assert response.status_code == 200
    assert response.get_json() == {}

    # Checking that the patches were applied.
    response: TestResponse = client.get(f"/v1/{resource_name}")
    assert response.status_code == 200
    assert response.get_json() == {str(rs_id): full_patch}

    response: TestResponse = client.get(f"/v1/{resource_name}/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == full_patch

    # Delete the folder
    response: TestResponse = client.delete(f"/v1/{resource_name}/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == {}

    # Check that the folder was deleted
    response: TestResponse = client.get(f"/v1/{resource_name}")
    assert response.status_code == 200
    assert response.get_json() == {}

    # Checking that trailing slashes work too
    response: TestResponse = client.post(f"/v1/{resource_name}/", json=initial_data)
    assert response.status_code == 201
    rs_id = response.get_json()["id"]

    response: TestResponse = client.get(f"/v1/{resource_name}/")
    assert response.status_code == 200
    assert response.get_json() == {str(rs_id): initial_data}


@authenticated
def test_documents_work(client):
    full_data = {
        "filename": "exam.pdf",
        "downloadable": False,
        "content_type": "application/pdf"
    }
    partial_patch = {
        "downloadable": True
    }
    full_patch = {
        "filename": "exam.tex",
        "downloadable": True,
        "content_type": "application/x-latex"
    }
    template_test_resource(client, "documents", full_data, partial_patch, full_patch)


@authenticated
def _create_doc(client, filename, content_type, downloadable):
    res = client.post("/v1/documents", json={
        "filename": filename,
        "content_type": content_type,
        "downloadable": downloadable
    })
    return res.get_json()["id"]


@authenticated
def _upload_doc(client, doc_id, content_type, data):
    response = client.post(f"/v1/upload?id={doc_id}", content_type=content_type, data=data)
    assert response.status_code == 200
    assert response.get_json() == {}


def test_authenticated_upload_download(client):
    doc_id = _create_doc(client, "a.txt", "text/plain", True)
    _upload_doc(client, doc_id, "text/plain", b"Hello World")

    login(client)
    response = client.get(f"/v1/download?id={doc_id}")
    assert response.status_code == 200
    assert response.data == b"Hello World"
    assert response.content_type == "text/plain; charset=utf-8"
    logout(client)


def test_unauthenticated_upload_download(client):
    doc_id = _create_doc(client, "b.txt", "text/plain", False)

    response = client.post(f"/v1/upload?id={doc_id}", content_type="text/plain", data=b"Hello World")
    assert response.status_code == 401

    _upload_doc(client, doc_id, "text/plain", b"Hello World")

    response = client.get(f"/v1/download?id={doc_id}")
    assert response.status_code == 404


@authenticated
def test_courses_work(client):
    full_data = {
        "long_name": "Rocket Sceince",
        "short_name": "RS"
    }
    partial_path = {
        "long_name": "Rocket Science"
    }
    full_patch = {
        "long_name": "Foundations of Rocket Science",
        "short_name": "FRS"
    }
    template_test_resource(client, "courses", full_data, partial_path, full_patch)


@authenticated
def test_folders_work(client):
    full_data = {
        "name": "Rocket Science"
    }
    partial_patch = {}
    full_patch = {
        "name": "Foundations of Rocket Science"
    }
    template_test_resource(client, "folders", full_data, partial_patch, full_patch)


@authenticated
def test_authors_work(client):
    full_data = {
        "name": "John Doe"
    }
    partial_patch = {}
    full_patch = {
        "name": "John Mustermann-Doe"
    }
    template_test_resource(client, "authors", full_data, partial_patch, full_patch)


@authenticated
def test_items_work(client):
    doc_a = client.post("/v1/documents", json={
        "filename": "a.pdf",
        "downloadable": True,
        "content_type": "application/x-latex"
    }).get_json()["id"]
    doc_b = client.post("/v1/documents", json={
        "filename": "b.pdf",
        "downloadable": False,
        "content_type": "application/x-latex"
    }).get_json()["id"]

    course_a = client.post("/v1/courses", json={
        "long_name": "Rocket Science",
        "short_name": "RS"
    }).get_json()["id"]
    course_b = client.post("/v1/courses", json={
        "long_name": "Foundations of Rocket Science",
        "short_name": "FRS"
    }).get_json()["id"]

    folder_a = client.post("/v1/folders", json={
        "name": "Rocket Science"
    }).get_json()["id"]
    folder_b = client.post("/v1/folders", json={
        "name": "Foundations of Rocket Science"
    }).get_json()["id"]

    author_a = client.post("/v1/authors", json={
        "name": "Max Mustermann"
    }).get_json()["id"]
    author_b = client.post("/v1/authors", json={
        "name": "John Doe"
    }).get_json()["id"]

    full_data = {
        "name": "Foundations of Rocket Science",
        "date": None,
        "documents": [doc_a],
        "authors": [author_a],
        "courses": [course_a],
        "folders": [folder_a],
        "visible": False
    }
    partial_patch = {
        "date": "2021-01-01",
        "authors": [author_a, author_b]
    }
    full_patch = {
        "name": "Rocket Science",
        "date": "2021-12-24",
        "documents": [doc_a, doc_b],
        "authors": [author_a],
        "courses": [course_a, course_b],
        "folders": [folder_a, folder_b],
        "visible": True
    }

    template_test_resource(client, "items", full_data, partial_patch, full_patch)


def test_hidden_items(client):
    login(client)

    response: TestResponse = client.post("/v1/documents", json={
        "filename": "a.txt",
        "downloadable": False,
        "content_type": "text/plain",
    })
    assert response.status_code == 201
    document_id = response.json["id"]

    response: TestResponse = client.post("/v1/items", json={
        "name": "Foundations of Rocket Science",
        "date": None,
        "documents": [document_id],
        "authors": [],
        "courses": [],
        "folders": [],
        "visible": False
    })
    assert response.status_code == 201
    item_id = response.json["id"]

    def assert_entities_exist():
        assert len(client.get("/v1/items").json) == 1
        assert client.get(f"/v1/items/{item_id}").status_code == 200
        assert len(client.get("/v1/documents").json) == 1
        assert client.get(f"/v1/documents/{document_id}").status_code == 200

    def assert_entities_dont_exist():
        assert len(client.get("/v1/items").json) == 0
        assert client.get(f"/v1/items/{item_id}").status_code == 404
        assert len(client.get("/v1/documents").json) == 0
        assert client.get(f"/v1/documents/{document_id}").status_code == 404

    assert_entities_exist()
    logout(client)
    assert_entities_dont_exist()
    login(client)
    assert_entities_exist()
