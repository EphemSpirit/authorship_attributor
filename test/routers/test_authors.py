from fastapi import status
from app.extensions import get_db
from app.models import Author, AuthorStyleProfile
from test.utils import *
from test.fixtures.authors import test_author
from test.fixtures.author_style_profile import test_author_style_profile
from sqlalchemy.exc import IntegrityError
import pytest

app.dependency_overrides[get_db] = override_get_db


def test_get_authors_empty():
    response = client.get("/authors")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_get_authors(test_author: Author):
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


def test_create_author_duplicate(test_author: Author):
    payload = {
        "name": test_author.name,
        "author_metadata": {"bio": "He was a man", "age": 65}
    }

    with pytest.raises(IntegrityError):
        client.post("/authors", json=payload)


def test_get_author(test_author: Author):
    response = client.get(f"/authors/{test_author.id}")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == test_author.id
    assert body["name"] == test_author.name
    assert body["author_metadata"] == test_author.author_metadata


def test_get_author_not_found():
    response = client.get("/authors/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_author(test_author: Author):
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


def test_delete_author(test_author: Author):
    response = client.delete(f"/authors/{test_author.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = client.get(f"/authors/{test_author.id}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_author_not_found():
    response = client.delete("/authors/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_author_profile(test_author_style_profile: AuthorStyleProfile):
    response = client.get(f"/authors/{test_author_style_profile.author_id}/style-profile")

    assert response.status_code == status.HTTP_200_OK

    body = response.json()
    assert body["id"] == test_author_style_profile.id
    assert body["author_id"] == test_author_style_profile.author_id
    assert body["num_documents_used"] == test_author_style_profile.num_documents_used
    assert body["model_version"] == test_author_style_profile.model_version
    assert body["computed_at"] == test_author_style_profile.computed_at.isoformat()

    expected_feature = test_author_style_profile.features[0]
    assert len(body["features"]) == 1
    assert body["features"][0]["id"] == expected_feature.id
    assert body["features"][0]["feature_type"] == expected_feature.feature_type
    assert body["features"][0]["profile_vector"] == expected_feature.profile_vector
    assert body["features"][0]["feature_names"] == expected_feature.feature_names