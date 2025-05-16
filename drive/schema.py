from django.utils.autoreload import request_finished
import graphene
import graphql_jwt
from graphql_jwt.decorators import login_required
from graphene_django import DjangoObjectType
from .models import Folder, File, User # Import the File model

# Define a DjangoObjectType for the File model
class FileType(DjangoObjectType):
    class Meta:
        model = File
        fields = ("id", "user", "folder", "name", "file", "size", "created_at")

# Define a DjangoObjectType for the Folder model
class FolderType(DjangoObjectType):
    class Meta:
        model = Folder
        fields = ("id", "name", "user", "parent_folder", "created_at", "files", "folders")

class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "email",)

# Define the main Query class
class Query(graphene.ObjectType):
    viewer = graphene.Field(UserType)
    folders = graphene.List(FolderType, parent_folder_id=graphene.UUID(required=False))
    folder_by_id = graphene.Field(FolderType, id=graphene.UUID())
    files = graphene.List(FileType,folder_id=graphene.UUID(required=False))
    file_by_id = graphene.Field(FileType, id=graphene.UUID())

    @login_required
    def resolve_viewer(self, info):
        return info.context.user;

    def resolve_folders(self, info, parent_folder_id=None):
        if parent_folder_id is not None:
            return Folder.objects.filter(parent_folder_id=parent_folder_id)
        return Folder.objects.filter(parent_folder__isnull=True)

    def resolve_folder_by_id(self, info, id):
        try:
            return Folder.objects.get(pk=id)
        except Folder.DoesNotExist:
            return None

    def resolve_files(self, info, folder_id=None):
        if folder_id is not None:
            return File.objects.filter(folder_id=folder_id)
        return File.objects.filter(folder_id__isnull=True)

    def resolve_file_by_id(self, info, id):
        try:
            return File.objects.get(pk=id)
        except File.DoesNotExist:
            return None


class Mutation(graphene.ObjectType):
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


# Export the schema
schema = graphene.Schema(query=Query, mutation=Mutation)
