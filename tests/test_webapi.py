import tempfile
from functools import wraps
from typing import Callable, Dict

import pytest
from flask import session
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from klausurarchiv import create_app


@pytest.fixture
def client() -> FlaskClient:
    with tempfile.TemporaryDirectory() as tempdir:
        app = create_app({"TESTING": True, "ARCHIVE_PATH": tempdir})

        with app.test_client() as client:
            yield client


def login(client: FlaskClient, username: str, password: str):
    return client.post("/v1/login", json={
        "username": username,
        "password": password
    })


def logout(client: FlaskClient):
    return client.post("/v1/logout")


def authenticated(function: Callable):
    @wraps(function)
    def wrapper(client: FlaskClient, *args, **kwargs):
        login(client, "john", "4711")
        result = function(client, *args, **kwargs)
        logout(client)
        return result

    return wrapper


def test_login_logout(client: FlaskClient):
    # Logging out with being logged in
    response: TestResponse = logout(client)
    assert response.status_code == 200
    assert response.get_json() == {}
    assert "username" not in session

    # Logging in
    response: TestResponse = login(client, "john", "4711")
    assert response.status_code == 200
    assert response.get_json() == {}
    assert session["username"] == "john"

    # Logging in again, should not change state
    response: TestResponse = login(client, "john", "4711")
    assert response.status_code == 200
    assert response.get_json() == {}
    assert session["username"] == "john"

    # Logging out
    response: TestResponse = logout(client)
    assert response.status_code == 200
    assert response.get_json() == {}
    assert "username" not in session

    # Trying to log in with invalid credentials
    response: TestResponse = client.post("/v1/login", json={
        "username": "jane",
        "password": "1612"
    })
    assert response.status_code == 401
    assert "message" in response.get_json()
    assert "username" not in session


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
