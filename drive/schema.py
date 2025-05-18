import graphene
import graphql_jwt
from graphql_jwt.decorators import login_required
from graphene_django import DjangoObjectType
from graphene_file_upload.scalars import Upload

from .models import Folder, File, User

# GraphQL Types
class FileType(DjangoObjectType):
    class Meta:
        model = File
        fields = ("id", "user", "folder", "name", "file", "size", "created_at")

class FolderType(DjangoObjectType):
    class Meta:
        model = Folder
        fields = ("id", "name", "user", "parent_folder", "created_at", "files", "folders")

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


# Schema mutation registry
class Mutation(graphene.ObjectType):
    update_file = UpdateFileMutation.Field()
    create_file = CreateFileMutation.Field()
    delete_file = DeleteFileMutation.Field()
    create_folder = CreateFolderMutation.Field()
    delete_folder = DeleteFolderMutation.Field()
    update_folder = UpdateFolderMutation.Field()

    # JWT auth
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


# Final schema
schema = graphene.Schema(query=Query, mutation=Mutation)
