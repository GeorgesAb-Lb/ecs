from django.db import models
from ecs.authorization.managers import AuthorizationManager


class NotificationQuerySet(models.QuerySet):
    def answered(self):
        return self.filter(models.Q(answer__isnull=False) | models.Q(safetynotification__is_acknowledged=True))
        
    def unanswered(self):
        return self.filter(models.Q(answer__isnull=True) & (models.Q(safetynotification__isnull=True) | models.Q(safetynotification__is_acknowledged=False)))

    def pending(self):
        return self.unanswered() | self.filter(answer__published_at__isnull=True)


NotificationManager = AuthorizationManager.from_queryset(NotificationQuerySet)