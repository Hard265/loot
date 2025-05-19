import uuid
import os
import magic
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from drive.managers import FileQuerySet, FolderQuerySet

User = get_user_model()


def user_directory_path(instance, filename):
    """Generate a unique file path for uploaded files using the user's email and a UUID.
    
    Args:
        instance: The File model instance
        filename: Original filename of the uploaded file
        
    Returns:
        str: Path where the file will be stored (e.g., 'user@example.com/uuid-filename.ext')
    """
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(instance.user.email, filename)


class Folder(models.Model):
    """Represents a folder that can contain files and other folders.
    
    Attributes:
        id: Unique identifier for the folder (UUID)
        user: Owner of the folder
        parent_folder: Parent folder if this is a subfolder (nullable)
        name: Name of the folder (alphanumeric with some special chars allowed)
        created_at: Timestamp when folder was created
    """
    
    objects = FolderQuerySet.as_manager()
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the folder"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="folders",
        help_text="User who owns this folder"
    )
    parent_folder = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="folders",
        help_text="Parent folder if this is a subfolder"
    )
    name = models.CharField(
        max_length=255, 
        validators=[RegexValidator(
            regex=r'^[a-zA-Z0-9_\-\.]+$',
            message='Folder name can only contain letters, numbers, underscores, hyphens, and periods'
        )],
        help_text="Name of the folder. Allowed characters: letters, numbers, _, -, ."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the folder was created"
    )
    
    def has_permission(self, user, required_permission='view'):
        """Check if a user has the required permission on this folder."""
        if user == self.user:
            return True
        
        try:
            share = Share.objects.get(
                models.Q(folder=self) | models.Q(folder__in=self.get_ancestors()),
                shared_with=user,
                is_active=True
            )
            if share.expires_at and share.expires_at < timezone.now():
                return False
                
            permission_order = ['view', 'edit', 'manage']
            return permission_order.index(share.permission) >= permission_order.index(required_permission)
        except Share.DoesNotExist:
            return False

    def share(self, with_user, permission='view', expires=None):
        """Share this folder with another user."""
        return Share.objects.create(
            shared_by=self.user,
            shared_with=with_user,
            folder=self,
            permission=permission,
            expires_at=expires
        )

    def get_shared_with(self):
        """Get all users this folder is shared with."""
        return User.objects.filter(
            shared_with_me__folder=self,
            shared_with_me__is_active=True
        ).distinct()

    def get_shared_by(self):
        """Get all users who shared this folder with me."""
        return User.objects.filter(
            shared_by_me__folder=self,
            shared_with_me=self.user,
            shared_with_me__is_active=True
        ).distinct()
    
    def save(self, *args, **kwargs):
        """Override save method to automatically set user if not provided."""
        if not self.user:
            self.user = self._state.adding and kwargs.get('user', None)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "Folder"
        verbose_name_plural = "Folders"
        ordering = ['-created_at']
        unique_together = ['user', 'parent_folder', 'name']


class File(models.Model):
    """Represents an uploaded file with metadata.
    
    Attributes:
        id: Unique identifier for the file (UUID)
        user: Owner of the file
        folder: Folder containing this file (nullable)
        name: Display name of the file
        file: Actual file data stored in the filesystem
        mime_type: Detected MIME type of the file
        size: Size of the file in bytes
        created_at: Timestamp when file was uploaded
    """
    
    objects = FileQuerySet.as_manager()
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the file"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="files",
        help_text="User who uploaded this file"
    )
    folder = models.ForeignKey(
        Folder, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name="files",
        help_text="Folder where this file is stored"
    )
    name = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Display name for the file (defaults to original filename if not provided)"
    )
    file = models.FileField(
        upload_to=user_directory_path,
        help_text="The actual file to upload"
    )
    mime_type = models.CharField(
        max_length=100, 
        blank=True, 
        editable=False,
        help_text="Automatically detected MIME type of the file"
    )
    size = models.BigIntegerField(
        editable=False,
        help_text="Size of the file in bytes"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the file was uploaded"
    )
    
    def has_permission(self, user, required_permission='view'):
        """Check if a user has the required permission on this file."""
        if user == self.user:
            return True
            
        # Check direct file shares
        try:
            share = Share.objects.get(
                file=self,
                shared_with=user,
                is_active=True
            )
            if share.expires_at and share.expires_at < timezone.now():
                return False
                
            permission_order = ['view', 'edit', 'manage']
            return permission_order.index(share.permission) >= permission_order.index(required_permission)
        except Share.DoesNotExist:
            pass
            
        # Check folder shares that might include this file
        if self.folder:
            return self.folder.has_permission(user, required_permission)
            
        return False

    def share(self, with_user, permission='view', expires=None):
        """Share this file with another user."""
        return Share.objects.create(
            shared_by=self.user,
            shared_with=with_user,
            file=self,
            permission=permission,
            expires_at=expires
        )

    def get_shared_with(self):
        """Get all users this file is shared with."""
        return User.objects.filter(
            shared_with_me__file=self,
            shared_with_me__is_active=True
        ).distinct()

    def get_shared_by(self):
        """Get all users who shared this file with me."""
        return User.objects.filter(
            shared_by_me__file=self,
            shared_with_me=self.user,
            shared_with_me__is_active=True
        ).distinct()

    def clean(self):
        """Detect MIME type when cleaning the model."""
        super().clean()
        if self.file:
            mime = magic.from_buffer(self.file.read(1024), mime=True)
            self.mime_type = mime
            self.file.seek(0)

    def save(self, *args, **kwargs):
        """Override save method to set user, name, and size automatically."""
        if not self.user:
            self.user = self._state.adding and kwargs.get('user', None)
        if not self.name:
            self.name = self.file.name
        self.size = self.file.size
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = "File"
        verbose_name_plural = "Files"
        ordering = ['-created_at']


class Share(models.Model):
    """Represents a shared file or folder with specific permissions."""
    
    class PermissionChoices(models.TextChoices):
        VIEW = 'view', 'Can view'
        EDIT = 'edit', 'Can edit'
        MANAGE = 'manage', 'Can manage'

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the share"
    )
    shared_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_by_me',
        help_text="User who is sharing the item"
    )
    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_with_me',
        help_text="User with whom the item is being shared"
    )
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shares',
        help_text="Shared file (if sharing a file)"
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shares',
        help_text="Shared folder (if sharing a folder)"
    )
    permission = models.CharField(
        max_length=10,
        choices=PermissionChoices.choices,
        default=PermissionChoices.VIEW,
        help_text="Permission level for the shared item"
    )
    shared_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the item was shared"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for the share"
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        default=uuid.uuid4,
        help_text="Unique token for link-based sharing"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the share is currently active"
    )

    class Meta:
        unique_together = [
            ('shared_with', 'file'),
            ('shared_with', 'folder')
        ]
        ordering = ['-shared_at']
        verbose_name = "Share"
        verbose_name_plural = "Shares"

    def clean(self):
        """Validate that either file or folder is set, but not both."""
        if not self.file and not self.folder:
            raise ValidationError("You must share either a file or a folder.")
        if self.file and self.folder:
            raise ValidationError("You cannot share both a file and a folder at the same time.")

    def __str__(self):
        item = self.file if self.file else self.folder
        return f"{self.shared_by} shared {item} with {self.shared_with} ({self.permission})"

class ShareLink(models.Model):
    """Represents a public share link for files or folders."""
    
    class PermissionChoices(models.TextChoices):
        VIEW = 'view', 'Can view'
        EDIT = 'edit', 'Can edit'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the share link"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_share_links',
        help_text="User who created the share link"
    )
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='share_links',
        help_text="Shared file (if sharing a file)"
    )
    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='share_links',
        help_text="Shared folder (if sharing a folder)"
    )
    permission = models.CharField(
        max_length=10,
        choices=PermissionChoices.choices,
        default=PermissionChoices.VIEW,
        help_text="Permission level for the shared item"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the share link was created"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for the share link"
    )
    password = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Optional password protection"
    )
    download_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times the item has been downloaded via this link"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the share link is currently active"
    )

    class Meta:
        verbose_name = "Share Link"
        verbose_name_plural = "Share Links"
        ordering = ['-created_at']

    def clean(self):
        """Validate that either file or folder is set, but not both."""
        if not self.file and not self.folder:
            raise ValidationError("You must share either a file or a folder.")
        if self.file and self.folder:
            raise ValidationError("You cannot share both a file and a folder at the same time.")

    def get_absolute_url(self):
        """Get the public URL for this share link."""
        from django.urls import reverse
        return reverse('share-link', kwargs={'token': self.id})

    def increment_download_count(self):
        """Increment the download counter."""
        self.download_count = self.download_count + 1
        self.save(update_fields=['download_count'])

    def __str__(self):
        item = self.file if self.file else self.folder
        return f"Public share link for {item} (created by {self.created_by})"
