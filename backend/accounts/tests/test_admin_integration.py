# accounts/tests/test_admin_integration.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from accounts.models import AdminProfile, AdminRole
from audit.models import AdminAuditLog, AdminActionType

User = get_user_model()

# (The temporary urlpatterns block has been deleted)

class AdminSuspendUserIntegrationTests(APITestCase):
    # (The urls = __name__ line has been deleted)

    def setUp(self):
        # Create a Risk Officer
        self.risk_admin = User.objects.create_user(email="risk@example.com", password="pw")
        AdminProfile.objects.create(user=self.risk_admin, role=AdminRole.RISK_OFFICER, is_active=True)

        # Create a standard user (the target)
        self.target_user = User.objects.create_user(email="target@example.com", password="pw")
        
        # FIX: Point exactly to the real name we used in accounts/urls.py
        # If you added app_name = 'accounts' in urls.py, use 'accounts:admin-suspend-user'
        # If you didn't use app_name, just use 'admin-suspend-user'
        try:
            self.url = reverse('accounts:admin-suspend-user', kwargs={'user_id': self.target_user.id})
        except:
            self.url = reverse('admin-suspend-user', kwargs={'user_id': self.target_user.id})

    def test_risk_officer_can_suspend_user_and_creates_audit_log(self):
        self.client.force_authenticate(user=self.risk_admin)
        
        payload = {"justification": "Detected multi-accounting fraud."}
        response = self.client.post(self.url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user state changed
        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)

        # Verify Immutable Audit Log was created
        self.assertEqual(AdminAuditLog.objects.count(), 1)
        log = AdminAuditLog.objects.first()
        self.assertEqual(log.admin, self.risk_admin)
        self.assertEqual(log.action_type, AdminActionType.SUSPEND_USER)
        self.assertEqual(log.justification, payload["justification"])
        self.assertEqual(log.new_state["is_active"], False)

    def test_suspend_fails_without_justification(self):
        self.client.force_authenticate(user=self.risk_admin)
        
        response = self.client.post(self.url, {}) # Empty payload
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        
        # Verify no log was created and user is still active
        self.assertEqual(AdminAuditLog.objects.count(), 0)
        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)