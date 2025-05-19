from django.db import models
from datetime import datetime

class SharedItemQuerySet(models.QuerySet):
    def for_user(self, user):
        """Get all items shared with a specific user."""
        return self.filter(
            models.Q(shares__shared_with=user) |
            models.Q(folder__shares__shared_with=user),
            shares__is_active=True,
            shares__expires_at__gt=datetime.now() | models.Q(shares__expires_at__isnull=True)
        ).distinct()


class FileQuerySet(SharedItemQuerySet):
    def editable_by(self, user):
        """Get files that user can edit."""
        return self.for_user(user).filter(
            models.Q(shares__permission='edit') |
            models.Q(shares__permission='manage') |
            models.Q(folder__shares__permission='edit') |
            models.Q(folder__shares__permission='manage')
        )


class FolderQuerySet(SharedItemQuerySet):
    def editable_by(self, user):
        """Get folders that user can edit."""
        return self.for_user(user).filter(
            models.Q(shares__permission='edit') |
            models.Q(shares__permission='manage')
        )

