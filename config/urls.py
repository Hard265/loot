from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from graphene_file_upload.django import FileUploadGraphQLView

from drive.views import FolderViewSet, FileViewSet, ShareLinkAPIView
from accounts.views import (
    TokenObtainView,
    RegisterView,
    UserDetailView,
    PasswordResetView,
    PasswordResetConfirmView,

)

router = routers.DefaultRouter()
router.register("folders", FolderViewSet, basename="folder")
router.register("files", FileViewSet, basename="file")

urlpatterns = [
    path("", include("accounts.urls")),
    path("", include("drive.urls")),

    # Admin routes
    path("admin/", admin.site.urls),
    path("graphql/", csrf_exempt(FileUploadGraphQLView.as_view(graphiql=True))),
    # Authentication routes
    path("api/v1/token/", TokenObtainView.as_view(), name="token"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("api/v1/register/", RegisterView.as_view(), name="register"),
    # Password reset routes
    path("api/password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path("api/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # User routes
    path("api/user/", UserDetailView.as_view(), name="user-detail"),
    # API routes
    path("api/", include(router.urls)),
    path("api/share/<uuid:token>/", ShareLinkAPIView.as_view(), name="share-link"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
