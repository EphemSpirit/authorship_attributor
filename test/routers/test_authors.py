from fastapi import status
from app.extensions import get_db
from app.models import Author
from test.utils import *
from test.fixtures.authors import test_author

app.dependency_overrides[get_db] = override_get_db


def test_get_authors_empty():
    response = client.get("/authors")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_get_authors(test_author):
    response = client.get("/authors")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == test_author.id
    assert body[0]["name"] == test_author.name
    assert body[0]["author_metadata"] == test_author.author_metadata


def test_create_author():
    payload = {
        "name": "Stephen King",
        "author_metadata": {"bio": "He was a man", "age": 65}
    }

    response = client.post("/authors", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == payload["name"]
    assert body["author_metadata"] == payload["author_metadata"]


def test_get_author(test_author):
    response = client.get(f"/authors/{test_author.id}")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == test_author.id
    assert body["name"] == test_author.name
    assert body["author_metadata"] == test_author.author_metadata


def test_get_author_not_found():
    response = client.get("/authors/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_author(test_author):
    payload = {
        "name": "Updated Name",
        "author_metadata": {"bio": "Updated bio", "age": 51}
    }

    response = client.put(f"/authors/{test_author.id}", json=payload)

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == test_author.id
    assert body["name"] == payload["name"]
    assert body["author_metadata"] == payload["author_metadata"]

    get_response = client.get(f"/authors/{test_author.id}")
    assert get_response.json()["name"] == payload["name"]


def test_update_author_not_found():
    payload = {
        "name": "Doesn't Matter",
        "author_metadata": {}
    }

    response = client.put("/authors/999999", json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_author(test_author):
    response = client.delete(f"/authors/{test_author.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/authors/{test_author.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_author_not_found():
    response = client.delete("/authors/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND