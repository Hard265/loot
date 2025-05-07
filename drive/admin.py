from django.contrib import admin
from .models import Folder, File


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("id", "parent_folder", "name", "created_at")
    list_filter = ( "created_at",)
    raw_id_fields = ("parent_folder",)
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("id", "folder", "name", "file", "size", "created_at")
    list_filter = ("created_at",)
    raw_id_fields = ("folder",)
    search_fields = (
        "name",
        "folder__name",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    def size(self, obj):
        return obj.size()
