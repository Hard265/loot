from rest_framework import serializers
from .models import Folder, File

class FolderSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Folder
        fields = ["id", "parent_folder", "name", "created_at"]

class FileSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = File
        fields = ["id", "folder", "name", "file", "size","mime_type", "created_at"]
