# audit/services.py
from django.contrib.contenttypes.models import ContentType
from .models import PlatformEvent, AdminAuditLog, EventVisibility

class AuditLogger:
    @staticmethod
    def log_event(event_type, target, actor=None, event_data=None, visibility=EventVisibility.SYSTEM):
        """
        Logs a general platform event.
        Usage: AuditLogger.log_event('ESCROW_LOCKED', contract_instance, actor=request.user, visibility='PUBLIC')
        """
        if event_data is None:
            event_data = {}
            
        content_type = ContentType.objects.get_for_model(target)
        
        return PlatformEvent.objects.create(
            event_type=event_type,
            actor=actor,
            content_type=content_type,
            object_id=target.pk,
            event_data=event_data,
            visibility=visibility
        )

    @staticmethod
    def log_admin_action(admin, action_type, target, justification, previous_state=None, new_state=None, ip_address=None):
        """
        Logs a high-security admin intervention.
        Usage: AuditLogger.log_admin_action(request.user, AdminActionType.SUSPEND_USER, user_instance, "Fraud detected")
        """
        content_type = ContentType.objects.get_for_model(target)
        
        return AdminAuditLog.objects.create(
            admin=admin,
            action_type=action_type,
            content_type=content_type,
            object_id=target.pk,
            previous_state=previous_state,
            new_state=new_state,
            justification=justification,
            ip_address=ip_address
        )