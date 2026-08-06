import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        SECURITY_ALERT = 'SECURITY', 'Security Alert'
        ACCOUNT_UPDATE = 'ACCOUNT', 'Account Update'
        ESCROW_ALERT = 'ESCROW', 'Escrow Alert'
        GENERAL = 'GENERAL', 'General System Message'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(
        max_length=20, 
        choices=NotificationType.choices, 
        default=NotificationType.GENERAL
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"