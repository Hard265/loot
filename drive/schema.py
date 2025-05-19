from datetime import datetime
import graphene
from graphql import GraphQLError
import graphql_jwt
from graphql_jwt.decorators import login_required
from graphene_django import DjangoObjectType
from graphene_file_upload.scalars import Upload
from django.contrib.auth import get_user_model

from .models import Folder, File, Share, ShareLink

User = get_user_model()

# GraphQL Types
class FileType(DjangoObjectType):
    class Meta:
        model = File
        fields = ("id", "user", "folder", "name", "file", "mime_type", "size", "created_at")

    def resolve_file(self, info):
        request = info.context
        if self.file:
            return self.file.url
        return None

class FolderType(DjangoObjectType):
    class Meta:
        model = Folder
        fields = ("id", "name", "user", "parent_folder", "created_at", "files", "folders")

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

class CreateShare(graphene.Mutation):
    class Arguments:
        file_id = graphene.UUID(required=False)
        folder_id = graphene.UUID(required=False)
        shared_with_id = graphene.UUID(required=True)
        permission = graphene.String(default_value="view")
        expires_at = graphene.DateTime(required=False)

    share = graphene.Field(ShareType)

    @login_required
    def mutate(self, info, shared_with_id, permission, file_id=None, folder_id=None, expires_at=None):
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
            raise Exception("Must provide file_id or folder_id")

        return CreateShare(share=share)

class CreateShareLink(graphene.Mutation):
    class Arguments:
        file_id = graphene.UUID(required=False)
        folder_id = graphene.UUID(required=False)
        permission = graphene.String(default_value="view")
        expires_at = graphene.DateTime(required=False)
        password = graphene.String(required=False)

    share_link = graphene.Field(ShareLinkType)

    @login_required
    def mutate(self, info, permission, file_id=None, folder_id=None, expires_at=None, password=None):
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
            raise Exception("Must provide file_id or folder_id")

        return CreateShareLink(share_link=link)

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

    # JWT auth
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


# Final schema
schema = graphene.Schema(query=Query, mutation=Mutation)
