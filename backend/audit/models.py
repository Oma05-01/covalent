# audit/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# ---------------------------------------------------------
# 1. PLATFORM EVENTS (The Universal Ledger)
# Tracks everything: user actions, system actions, escrow locks.
# ---------------------------------------------------------

class EventVisibility(models.TextChoices):
    SYSTEM = 'SYSTEM', 'System/DevOps Only'
    ADMIN = 'ADMIN', 'Admins & Risk Officers'
    PARTICIPANTS = 'PARTICIPANTS', 'Contract/Dispute Participants'
    PUBLIC = 'PUBLIC', 'Publicly Viewable (Redacted)'

class PlatformEvent(models.Model):
    event_type = models.CharField(max_length=100, db_index=True) # e.g., 'ESCROW_LOCKED', 'USER_REGISTERED'
    
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    
    # What was touched? (Contract, User, Escrow)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.CharField(max_length=255)
    target_object = GenericForeignKey('content_type', 'object_id')
    
    event_data = models.JSONField(default=dict)
    visibility = models.CharField(max_length=20, choices=EventVisibility.choices, default=EventVisibility.SYSTEM)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"


# ---------------------------------------------------------
# 2. ADMIN AUDIT LOGS (High-Security Back-Office Tracking)
# Strictly tracks when staff members manipulate system state.
# ---------------------------------------------------------

class AdminActionType(models.TextChoices):
    SUSPEND_USER = 'SUSPEND_USER', 'Suspend User'
    UNSUSPEND_USER = 'UNSUSPEND_USER', 'Unsuspend User'
    ADJUST_TRUST_SCORE = 'ADJUST_TRUST_SCORE', 'Adjust Trust Score'
    RESOLVE_DISPUTE = 'RESOLVE_DISPUTE', 'Resolve Dispute'
    REVERSE_TRANSACTION = 'REVERSE_TRANSACTION', 'Reverse Transaction'

class AdminAuditLog(models.Model):
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='admin_action_logs'
    )
    action_type = models.CharField(max_length=50, choices=AdminActionType.choices)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.CharField(max_length=255)
    target_object = GenericForeignKey('content_type', 'object_id')
    
    previous_state = models.JSONField(null=True, blank=True)
    new_state = models.JSONField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    justification = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['action_type']),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Admin audit logs are immutable and cannot be modified.")
        super().save(*args, **kwargs)