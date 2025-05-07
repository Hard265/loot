import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        email="testuser@example.com", password="password123"
    )


def test_register_user(api_client):
    response = api_client.post(
        "/api/v1/users/", {"email": "newuser@example.com", "password": "password123"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["email"] == "newuser@example.com"


def test_login_user(api_client, user):
    response = api_client.post(
        "/api/v1/token/", {"email": user.email, "password": "password123"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


def test_user_detail(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.get("/api/v1/whoami/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == user.email
