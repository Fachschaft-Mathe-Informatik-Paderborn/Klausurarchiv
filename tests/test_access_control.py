import flask.testing

from klausurarchiv import create_app


def build_context(access_rules) -> flask.testing.Client:
    app = create_app({
        "TESTING": True,
        "ACCESS": access_rules
    })
    return app.test_client()


def test_wildcard_allow():
    rules = {
        "*": {
            "allow": ["127.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 200

    rules = {
        "*": {
            "allow": ["10.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 401


def test_wildcard_deny():
    rules = {
        "*": {
            "deny": ["127.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 401

    rules = {
        "*": {
            "deny": ["10.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 200


def test_specific_allow():
    rules = {
        "items": {
            "allow": ["127.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 200
        assert client.get("/v1/authors").status_code == 200

    rules = {
        "items": {
            "allow": ["10.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 401
        assert client.get("/v1/authors").status_code == 200


def test_specific_deny():
    rules = {
        "items": {
            "deny": ["127.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 401
        assert client.get("/v1/authors").status_code == 200

    rules = {
        "items": {
            "deny": ["10.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 200
        assert client.get("/v1/authors").status_code == 200


def test_specialization():
    rules = {
        "*": {
          "deny": ["127.0.0.0/24"]
        },
        "items": {
            "allow": ["127.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 200
        assert client.get("/v1/authors").status_code == 401

    rules = {
        "*": {
          "allow": ["127.0.0.0/24"]
        },
        "items": {
            "deny": ["127.0.0.0/24"]
        }
    }
    with build_context(rules) as client:
        assert client.get("/v1/items").status_code == 401
        assert client.get("/v1/authors").status_code == 200
