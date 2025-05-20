from datetime import datetime
import graphene
from graphql import GraphQLError
import graphql_jwt
from graphql_jwt.decorators import login_required
from graphene_django import DjangoObjectType
from graphene_file_upload.scalars import Upload
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Folder, File, Share, ShareLink

User = get_user_model()

# GraphQL Types
class FileType(DjangoObjectType):
    class Meta:
        model = File
        fields = ("id", "user", "folder", "name", "file", "mime_type", "size", "created_at", "shares", "share_links", "has_shares", "has_share_links")
    
    has_shares = graphene.Boolean();
    has_share_links = graphene.Boolean();

    def resolve_file(self, info):
        if self.file:
            return self.file.url
        return None

    def resolve_has_shares(self, info):
        # only for this file owner
        if self.user != info.context.user:
            return False
        return self.shares.exists()

    def resolve_has_share_links(self, info):
        # only for this file owner
        if self.user != info.context.user:
            return False
        return self.share_links.exists()

class FolderType(DjangoObjectType):
    class Meta:
        model = Folder
        fields = ("id", "name", "user", "parent_folder", "created_at", "has_shares", "has_share_links", "files", "folders")

    has_shares = graphene.Boolean();
    has_share_links = graphene.Boolean();

    def resolve_has_shares(self, info):
        if self.user != info.context.user:
            return False
        return self.shares.exists()

    def resolve_has_share_links(self, info):
        if self.user != info.context.user:
            return False
        return self.share_links.exists()

class ShareType(DjangoObjectType):
    class Meta:
        model = Share
        fields = (
            "id", "shared_by", "shared_with", "file", "folder",
            "permission", "shared_at", "expires_at", "token", "is_active"
        )

class ShareLinkType(DjangoObjectType):
    class Meta:
        model = ShareLink
        fields = (
            "id", "created_by", "file", "folder", "permission",
            "created_at", "expires_at", "password", "download_count", "is_active"
        )

class ShareLinkUnion(graphene.Union):
    class Meta:
        types = (FileType, FolderType)
        description = "Returns a File or Folder depending on what was shared"

class ContentUnion(graphene.Union):
    class Meta:
        types = (FileType, FolderType)
        description = "Returns either a File or a Folder"

class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "email",)


# Query
class Query(graphene.ObjectType):
    viewer = graphene.Field(UserType)
    folders = graphene.List(FolderType, parent_folder_id=graphene.UUID(required=False))
    folder_by_id = graphene.Field(FolderType, id=graphene.UUID())
    files = graphene.List(FileType, folder_id=graphene.UUID(required=False))
    file_by_id = graphene.Field(FileType, id=graphene.UUID())
    shares = graphene.List(ShareType)
    share_links = graphene.List(ShareLinkType)
    share_link = graphene.Field(
        ShareLinkUnion,
        token=graphene.UUID(required=True),
        password=graphene.String(required=False)
    )
    search = graphene.List(
        ContentUnion,
        query=graphene.String(required=True)
    )
    contents = graphene.List(
        ContentUnion,
        folder_id=graphene.UUID(required=False)
    )

    @login_required
    def resolve_viewer(self, info):
        return info.context.user

    @login_required
    def resolve_folders(self, info, parent_folder_id=None):
        user = info.context.user
        qs = user.folders.all()
        if parent_folder_id is not None:
            qs = qs.filter(parent_folder_id=parent_folder_id)
        else:
            qs = qs.filter(parent_folder__isnull=True)
        return qs

    @login_required
    def resolve_folder_by_id(self, info, id):
        return info.context.user.folders.filter(pk=id).first()

    @login_required
    def resolve_files(self, info, folder_id=None):
        user = info.context.user
        qs = user.files.all()
        if folder_id is not None:
            qs = qs.filter(folder_id=folder_id)
        else:
            qs = qs.filter(folder__isnull=True)
        return qs

    @login_required
    def resolve_file_by_id(self, info, id):
        return info.context.user.files.filter(pk=id).first()

    @login_required
    def resolve_shares(self, info):
        return Share.objects.filter(shared_by=info.context.user)

    @login_required
    def resolve_share_links(self, info):
        return ShareLink.objects.filter(created_by=info.context.user)

    def resolve_share_link(self, info, token, password=None):
        try:
            link = ShareLink.objects.select_related("file", "folder").get(id=token, is_active=True)
        except ShareLink.DoesNotExist:
            raise GraphQLError("Invalid or inactive share link")

        if link.expires_at and link.expires_at < datetime.now():
            raise GraphQLError("This share link has expired")

        if link.password and password != link.password:
            raise GraphQLError("Incorrect or missing password")

        link.increment_download_count()
        return link.file if link.file else link.folder

    @login_required
    def resolve_search(self, info, query):
        user = info.context.user
        file_results = File.objects.filter(
            user=user,
            name__icontains=query  # Case-insensitive search
        )
        folder_results = Folder.objects.filter(
            user=user,
            name__icontains=query
        )
        return list(file_results) + list(folder_results)

    @login_required
    def resolve_contents(self, info, folder_id=None):
        user = info.context.user
        items = []
        if folder_id:
            try:
                folder = Folder.objects.get(pk=folder_id, user=user)
                files = File.objects.filter(user=user, folder=folder)
                folders = Folder.objects.filter(user=user, parent_folder=folder)
                items.extend(list(files))
                items.extend(list(folders))
            except Folder.DoesNotExist:
                raise GraphQLError("Folder not found or unauthorized")
        else:
            # Fetch root level contents (files with no folder and folders with no parent)
            files = File.objects.filter(user=user, folder__isnull=True)
            folders = Folder.objects.filter(user=user, parent_folder__isnull=True)
            items.extend(list(files))
            items.extend(list(folders))
        return items

# Mutations
class UpdateFileMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)

    file = graphene.Field(FileType)

    @login_required
    def mutate(self, info, id, name):
        user = info.context.user
        file = user.files.filter(pk=id).first()
        if not file:
            raise Exception("Not found or unauthorized")
        file.name = name
        file.save()
        return UpdateFileMutation(file=file)


class CreateFileMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=False)
        folder_id = graphene.UUID(required=False)
        file = Upload(required=True)

    file = graphene.Field(FileType)

    @login_required
    def mutate(self, info, file, name=None, folder_id=None):
        user = info.context.user
        folder = user.folders.filter(pk=folder_id).first() if folder_id else None
        file_instance = File.objects.create(
            user=user,
            name=name or file.name,
            folder=folder,
            file=file,
            size=file.size
        )
        return CreateFileMutation(file=file_instance)


class DeleteFileMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    success = graphene.Boolean()

    @login_required
    def mutate(self, info, id):
        user = info.context.user
        file = user.files.filter(pk=id).first()
        if file:
            file.delete()
            return DeleteFileMutation(success=True)
        return DeleteFileMutation(success=False)


class CreateFolderMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        parent_folder_id = graphene.UUID(required=False)

    folder = graphene.Field(FolderType)

    @login_required
    def mutate(self, info, name, parent_folder_id=None):
        user = info.context.user
        parent = user.folders.filter(pk=parent_folder_id).first() if parent_folder_id else None
        folder = Folder.objects.create(user=user, name=name, parent_folder=parent)
        return CreateFolderMutation(folder=folder)


class DeleteFolderMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    success = graphene.Boolean()

    @login_required
    def mutate(self, info, id):
        user = info.context.user
        folder = user.folders.filter(pk=id).first()
        if folder:
            folder.delete()
            return DeleteFolderMutation(success=True)
        return DeleteFolderMutation(success=False)


class UpdateFolderMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        name = graphene.String(required=True)

    folder = graphene.Field(FolderType)

    @login_required
    def mutate(self, info, id, name):
        user = info.context.user
        folder = user.folders.filter(pk=id).first()
        if not folder:
            raise Exception("Not found or unauthorized")
        folder.name = name
        folder.save()
        return UpdateFolderMutation(folder=folder)

PERMISSION_CHOICES = ["VIEW", "EDIT", "MANAGE"]

def validate_permission(permission):
    if permission not in PERMISSION_CHOICES:
        raise GraphQLError(f"Invalid permission. Allowed values are: {', '.join(PERMISSION_CHOICES)}")

class CreateShare(graphene.Mutation):
    class Arguments:
        file_id = graphene.UUID(required=False)
        folder_id = graphene.UUID(required=False)
        shared_with_id = graphene.UUID(required=True)
        permission = graphene.String(default_value="VIEW")
        expires_at = graphene.DateTime(required=False)

    share = graphene.Field(ShareType)

    @login_required
    def mutate(self, info, shared_with_id, permission, file_id=None, folder_id=None, expires_at=None):
        validate_permission(permission)
        user = info.context.user
        shared_with = User.objects.get(pk=shared_with_id)

        if file_id:
            file = File.objects.get(pk=file_id, user=user)
            share = Share.objects.create(
                shared_by=user, shared_with=shared_with,
                file=file, permission=permission,
                expires_at=expires_at
            )
        elif folder_id:
            folder = Folder.objects.get(pk=folder_id, user=user)
            share = Share.objects.create(
                shared_by=user, shared_with=shared_with,
                folder=folder, permission=permission,
                expires_at=expires_at
            )
        else:
            raise GraphQLError("Must provide file_id or folder_id")

        return CreateShare(share=share)

class CreateShareLink(graphene.Mutation):
    class Arguments:
        file_id = graphene.UUID(required=False)
        folder_id = graphene.UUID(required=False)
        permission = graphene.String(default_value="VIEW")
        expires_at = graphene.DateTime(required=False)
        password = graphene.String(required=False)

    share_link = graphene.Field(ShareLinkType)

    @login_required
    def mutate(self, info, permission, file_id=None, folder_id=None, expires_at=None, password=None):
        validate_permission(permission)
        user = info.context.user

        if file_id:
            file = File.objects.get(pk=file_id, user=user)
            link = ShareLink.objects.create(
                created_by=user, file=file,
                permission=permission,
                expires_at=expires_at,
                password=password
            )
        elif folder_id:
            folder = Folder.objects.get(pk=folder_id, user=user)
            link = ShareLink.objects.create(
                created_by=user, folder=folder,
                permission=permission,
                expires_at=expires_at,
                password=password
            )
        else:
            raise GraphQLError("Must provide file_id or folder_id")

        return CreateShareLink(share_link=link)

class UpdateShareMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        permission = graphene.String(required=False)
        expires_at = graphene.DateTime(required=False)
        is_active = graphene.Boolean(required=False)

    share = graphene.Field(ShareType)

    @login_required
    def mutate(self, info, id, **kwargs):
        user = info.context.user
        share = Share.objects.filter(pk=id, shared_by=user).first()
        if not share:
            raise GraphQLError("Share not found or unauthorized")

        if 'permission' in kwargs and kwargs['permission'] is not None:
            validate_permission(kwargs['permission'])

        allowed_fields = {'permission', 'expires_at', 'is_active'}
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(share, key, value)
        share.save()
        return UpdateShareMutation(share=share)

class DeleteShareMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    success = graphene.Boolean()

    @login_required
    def mutate(self, info, id):
        user = info.context.user
        share = Share.objects.filter(pk=id, shared_by=user).first()
        if share:
            share.delete()
            return DeleteShareMutation(success=True)
        return DeleteShareMutation(success=False)

class UpdateShareLinkMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)
        permission = graphene.String(required=False)
        expires_at = graphene.DateTime(required=False)
        password = graphene.String(required=False)
        is_active = graphene.Boolean(required=False)

    share_link = graphene.Field(ShareLinkType)

    @login_required
    def mutate(self, info, id, **kwargs):
        user = info.context.user
        share_link = ShareLink.objects.filter(pk=id, created_by=user).first()
        if not share_link:
            raise GraphQLError("Share link not found or unauthorized")

        if 'permission' in kwargs and kwargs['permission'] is not None:
            validate_permission(kwargs['permission'])

        allowed_fields = {'permission', 'expires_at', 'password', 'is_active'}
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(share_link, key, value)
        share_link.save()
        return UpdateShareLinkMutation(share_link=share_link)

class DeleteShareLinkMutation(graphene.Mutation):
    class Arguments:
        id = graphene.UUID(required=True)

    success = graphene.Boolean()

    @login_required
    def mutate(self, info, id):
        user = info.context.user
        share_link = ShareLink.objects.filter(pk=id, created_by=user).first()
        if share_link:
            share_link.delete()
            return DeleteShareLinkMutation(success=True)
        return DeleteShareLinkMutation(success=False)

# Schema mutation registry
class Mutation(graphene.ObjectType):
    update_file = UpdateFileMutation.Field()
    create_file = CreateFileMutation.Field()
    delete_file = DeleteFileMutation.Field()
    create_folder = CreateFolderMutation.Field()
    delete_folder = DeleteFolderMutation.Field()
    update_folder = UpdateFolderMutation.Field()
    create_share = CreateShare.Field()
    create_share_link = CreateShareLink.Field()
    update_share = UpdateShareMutation.Field()
    delete_share = DeleteShareMutation.Field()
    update_share_link = UpdateShareLinkMutation.Field()
    delete_share_link = DeleteShareLinkMutation.Field()

    # JWT auth
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


# Final schema
schema = graphene.Schema(query=Query, mutation=Mutation)

