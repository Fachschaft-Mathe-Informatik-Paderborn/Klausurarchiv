import json
import tempfile

import pytest
from klausurarchiv import create_app
from werkzeug.test import TestResponse
from functools import wraps
from flask import session


@pytest.fixture
def client():
    with tempfile.TemporaryDirectory() as tempdir:
        app = create_app({"TESTING": True, "ARCHIVE_PATH": tempdir})

        with app.test_client() as client:
            yield client


def login(client, username, password):
    return client.post("/v1/login", json={
        "username": username,
        "password": password
    })


def logout(client):
    return client.post("/v1/logout")


def authenticated(function):
    @wraps(function)
    def wrapper(client, *args, **kwargs):
        login(client, "john", "4711")
        result = function(client, *args, **kwargs)
        logout(client)
        return result
    return wrapper


def test_login_logout(client):
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


@authenticated
def test_folders_work(client):
    # Checking the initial state
    response: TestResponse = client.get("/v1/folders")
    assert response.status_code == 200
    assert response.get_json() == {}

    # Creating a new folder
    response: TestResponse = client.post("/v1/folders", json={
        "name": "Rocket Science"
    })
    assert response.status_code == 201
    rs_id = response.get_json()["id"]
    assert isinstance(rs_id, int)

    # Checking with the new folder was created
    response: TestResponse = client.get("/v1/folders")
    assert response.status_code == 200
    assert response.get_json() == {str(rs_id): {"name": "Rocket Science"}}

    # Checking whether the individual query works
    response: TestResponse = client.get(f"/v1/folders/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == {"name": "Rocket Science"}

    # Partial Patching
    response: TestResponse = client.patch(f"/v1/folders/{rs_id}", json={})
    assert response.status_code == 200
    assert response.get_json() == {}

    # Checking that nothing has changed.
    response: TestResponse = client.get(f"/v1/folders/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == {"name": "Rocket Science"}

    # Full Patching
    response: TestResponse = client.patch(f"/v1/folders/{rs_id}", json={
        "name": "Foundations of Rocket Science"
    })
    assert response.status_code == 200
    assert response.get_json() == {}

    # Checking if the patches were applied.
    response: TestResponse = client.get(f"/v1/folders/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == {"name": "Foundations of Rocket Science"}

    # Delete the folder
    response: TestResponse = client.delete(f"/v1/folders/{rs_id}")
    assert response.status_code == 200
    assert response.get_json() == {}

    # Check that the folder was deleted
    response: TestResponse = client.get("/v1/folders")
    assert response.status_code == 200
    assert response.get_json() == {}
