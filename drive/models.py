import uuid
import os
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()


def user_directory_path(instance, filename):
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(instance.user.email, filename)


class Folder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="folders"
    )
    parent_folder = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="folders",
    )
    name = models.CharField(max_length=255, validators=[RegexValidator(
            regex=r'^[a-zA-Z0-9_\-\.]+$',
            message='Invalid folder name'
        )])
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.user:
            self.user = self._state.adding and kwargs.get('user', None)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="files"
    )
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, null=True, blank=True,related_name="files")
    name = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=user_directory_path)
    size = models.BigIntegerField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.user:
            self.user = self._state.adding and kwargs.get('user', None)
        if not self.name:
            self.name = self.file.name
        self.size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)
