from django.test import TestCase
from django.contrib.auth import get_user_model
from audit.models import AdminAuditLog, AdminActionType
from audit.services import AuditLogger

User = get_user_model()

class AuditLoggerTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.com", password="pw")
        self.target_user = User.objects.create_user(email="target@example.com", password="pw")

    def test_log_admin_action_creates_record(self):
        """Proves the AuditLogger utility correctly generates a generic relation log."""
        log = AuditLogger.log_admin_action(
            admin=self.admin,
            action_type=AdminActionType.SUSPEND_USER,
            target=self.target_user,
            justification="Fraud detected",
            previous_state={"is_active": True},
            new_state={"is_active": False},
            ip_address="127.0.0.1"
        )
        
        self.assertEqual(AdminAuditLog.objects.count(), 1)
        self.assertEqual(log.admin, self.admin)
        self.assertEqual(log.target_object, self.target_user)
        self.assertEqual(log.new_state["is_active"], False)
        
    def test_admin_audit_log_is_immutable(self):
        """
        Business Rule Test: No silent trust score edits.
        Proves that an existing audit log cannot be updated or altered by anyone.
        """
        log = AuditLogger.log_admin_action(
            admin=self.admin,
            action_type=AdminActionType.ADJUST_TRUST_SCORE,
            target=self.target_user,
            justification="Manual adjustment"
        )
        
        # Attempting to edit an existing log should raise a PermissionError
        with self.assertRaises(PermissionError) as context:
            log.justification = "Hacked justification"
            log.save()
            
        self.assertIn("immutable", str(context.exception))