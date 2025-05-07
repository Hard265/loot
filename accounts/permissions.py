from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Permission to ensure the user is accessing their own data.
    """

    def has_permission(self, request, view):
        # Ensure the user is authenticated
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return obj == request.user
