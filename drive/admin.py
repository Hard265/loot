from django.contrib.admin import AdminSite
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Folder, File, Share, ShareLink


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "parent_folder", "created_at", "shared_status")
    list_filter = ("created_at", "user")
    search_fields = ("name", "user__email")
    autocomplete_fields = ("parent_folder", "user")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "shared_status")
    list_select_related = ("user", "parent_folder")
    
    def shared_status(self, obj):
        shares = obj.shares.filter(is_active=True).count()
        share_links = obj.share_links.filter(is_active=True).count()
        return format_html(
            "{} direct shares<br>{} public links",
            shares,
            share_links
        )
    shared_status.short_description = "Sharing Status"


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "folder", "size_display", "mime_type", "created_at", "shared_status")
    list_filter = ("created_at", "user", "mime_type")
    autocomplete_fields = ("folder", "user")
    search_fields = ("name", "folder__name", "user__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "mime_type", "size", "shared_status")
    
    def size_display(self, obj):
        return f"{obj.size / 1024:.1f} KB" if obj.size < 1024 * 1024 else f"{obj.size / (1024 * 1024):.1f} MB"
    size_display.short_description = "Size"
    
    def shared_status(self, obj):
        shares = obj.shares.filter(is_active=True).count()
        share_links = obj.share_links.filter(is_active=True).count()
        return format_html(
            "{} direct shares<br>{} public links",
            shares,
            share_links
        )
    shared_status.short_description = "Sharing Status"


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("shared_item", "shared_by", "shared_with", "permission", "shared_at", "expires_at", "is_active")
    list_filter = ("permission", "is_active", "shared_at")
    autocomplete_fields = ("shared_by", "shared_with", "file", "folder")
    search_fields = (
        "shared_by__email",
        "shared_with__email",
        "file__name",
        "folder__name"
    )
    ordering = ("-shared_at",)
    readonly_fields = ("shared_at", "token")
    list_select_related = ("shared_by", "shared_with", "file", "folder")
    
    def shared_item(self, obj):
        if obj.file:
            return format_html(
                "File: <a href='{}'>{}</a>",
                reverse("admin:drive_file_change", args=(obj.file.id,)),
                obj.file.name
            )
        else:
            return format_html(
                "Folder: <a href='{}'>{}</a>",
                reverse("admin:drive_folder_change", args=(obj.folder.id,)),
                obj.folder.name
            )
    shared_item.short_description = "Shared Item"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'shared_by', 'shared_with', 'file', 'folder'
        )


@admin.register(ShareLink)
class ShareLinkAdmin(admin.ModelAdmin):
    list_display = ("shared_item", "created_by", "permission", "created_at", "expires_at", "download_count", "is_active")
    list_filter = ("permission", "is_active", "created_at")
    autocomplete_fields = ("created_by", "file", "folder")
    search_fields = (
        "created_by__email",
        "file__name",
        "folder__name"
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "download_count", "id")
    list_select_related = ("created_by", "file", "folder")
    
    def shared_item(self, obj):
        if obj.file:
            return format_html(
                "File: <a href='{}'>{}</a>",
                reverse("admin:drive_file_change", args=(obj.file.id,)),
                obj.file.name
            )
        else:
            return format_html(
                "Folder: <a href='{}'>{}</a>",
                reverse("admin:drive_folder_change", args=(obj.folder.id,)),
                obj.folder.name
            )
    shared_item.short_description = "Shared Item"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by', 'file', 'folder'
        )

AdminSite.site_header = "Loot Administration"
AdminSite.site_title = "Loot Drive Admin"
AdminSite.index_title = "Welcome to Loot Drive Admin"
