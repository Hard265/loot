import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from drive.models import Folder, File, Share, ShareLink

User = get_user_model()

@pytest.fixture
def user(db):
    return User.objects.create_user(email='test@example.com', password='testpassword')

@pytest.mark.django_db
def test_create_folder_with_valid_data(user):
    folder = Folder.objects.create(user=user, name='My Folder')
    assert folder.name == 'My Folder'
    assert folder.user == user
    assert folder.id is not None
    assert folder.parent_folder is None

@pytest.mark.django_db
def test_create_folder_with_invalid_name(user):
    with pytest.raises(ValidationError) as excinfo:
        folder = Folder(user=user, name='Invalid Folder!')
        folder.full_clean()  # Explicitly call full_clean to trigger validation
        folder.save()
    assert "Folder name can only contain letters, numbers, underscores, hyphens, and periods" in excinfo.value.messages

@pytest.mark.django_db
def test_create_subfolder(user):
    parent_folder = Folder.objects.create(user=user, name='Parent Folder')
    subfolder = Folder.objects.create(user=user, name='Sub Folder', parent_folder=parent_folder)
    assert subfolder.parent_folder == parent_folder

@pytest.mark.django_db
def test_folder_name_unique_together(user):
    Folder.objects.create(user=user, name='Same Name')
    with pytest.raises(Exception):  # Should raise an IntegrityError or similar
        Folder.objects.create(user=user, name='Same Name')

@pytest.mark.django_db
def test_share_folder(user):
    folder = Folder.objects.create(user=user, name='Shared Folder')
    share = ShareLink.objects.create(folder=folder, created_by=user,)
    assert share.folder == folder
    assert share.created_by == user
