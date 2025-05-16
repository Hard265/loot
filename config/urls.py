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
from graphene_django.views import GraphQLView

from drive.views import FolderViewSet, FileViewSet
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
    # Admin routes
    path("admin/", admin.site.urls),

    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    # Authentication routes
    path("api/v1/token/", TokenObtainView.as_view(), name="token"),
    path("api/v1/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/v1/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("api/v1/register/", RegisterView.as_view(), name="register"),
    # Password reset routes
    path("api/v1/password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path("api/v1/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    # User routes
    path("api/v1/user/", UserDetailView.as_view(), name="user-detail"),
    # API routes
    path("api/v1/", include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
