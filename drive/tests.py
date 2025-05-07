import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Folder, File


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        email="testuser@example.com", password="password123"
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def folder(user):
    return Folder.objects.create(user=user, name="Test Folder")


@pytest.fixture
def file(user, folder):
    return File.objects.create(user=user, folder=folder, name="Test File", size=1024)


def test_folder_list(auth_client, folder):
    response = auth_client.get("/api/v1/folders/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["name"] == folder.name


def test_folder_create(auth_client):
    response = auth_client.post("/api/v1/folders/", {"name": "New Folder"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "New Folder"


def test_file_list(auth_client, file):
    response = auth_client.get("/api/v1/files/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["name"] == file.name


def test_file_create(auth_client, folder):
    response = auth_client.post(
        "/api/v1/files/",
        {"folder": str(folder.id), "name": "New File", "size": 2048},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["name"] == "New File"
