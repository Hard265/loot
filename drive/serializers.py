from rest_framework import serializers
from .models import Folder, File
from django.contrib.auth import get_user_model

class FolderSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Folder
        fields = ["id", "parent_folder", "name", "created_at"]

class FileSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = File
        fields = ["id", "folder", "name", "size", "created_at"]
