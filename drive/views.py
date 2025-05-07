from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action

from .models import Folder, File
from .serializers import FolderSerializer, FileSerializer


class FolderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = FolderPagination

    def get_queryset(self):
        sort_field = self.request.query_params.get(
            "s", "created_at"
        )  # Default to 'created_at'
        order = self.request.query_params.get(
            "o", "desc"
        )  # Default to descending order
        queryset = self.queryset.filter(user=self.request.user)

        if order == "asc":
            queryset = queryset.order_by(sort_field)
        elif order == "desc":
            queryset = queryset.order_by(f"-{sort_field}")
        return queryset

    @action(detail=True, methods=["get"], url_path="subfolders")
    def subfolders(self, request, pk=None):
        folder = self.get_object()
        subfolders = folder.folders.all()
        page = self.paginate_queryset(subfolders)
        if page is not None:
            serializer = FolderSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = FolderSerializer(subfolders, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="files")
    def files(self, request, pk=None):
        folder = self.get_object()
        files = folder.file_set.all()
        page = self.paginate_queryset(files)
        if page is not None:
            serializer = FileSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = FileSerializer(files, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        sort_field = self.request.query_params.get(
            "s", "created_at"
        )  # Default to 'created_at'
        order = self.request.query_params.get(
            "o", "desc"
        )  # Default to descending order
        queryset = self.queryset.filter(user=self.request.user)

        if order == "asc":
            queryset = queryset.order_by(sort_field)
        elif order == "desc":
            queryset = queryset.order_by(f"-{sort_field}")
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
