from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from accounts.models import AdminProfile, AdminRole
from audit.models import AdminAuditLog, AdminActionType

User = get_user_model()

class AdminGovernanceE2ETest(APITestCase):
    def setUp(self):
        # 1. Setup the Actors
        self.risk_admin = User.objects.create_user(email="risk_officer@example.com", password="pw", is_staff=True)
        AdminProfile.objects.create(user=self.risk_admin, role=AdminRole.RISK_OFFICER, is_active=True)
        
        self.fraudulent_vendor = User.objects.create_user(email="scammer_vendor@example.com", password="pw", role="VENDOR", is_active=True)

    def test_e2e_admin_investigates_and_penalizes_user(self):
        """
        E2E Flow: Admin searches for user -> Identifies them -> Suspends them -> Verifies Audit Log
        """
        self.client.force_authenticate(user=self.risk_admin)
        
        dashboard_url = reverse('admin_users') # FIX: Use your actual URL name
        search_response = self.client.get(f"{dashboard_url}?search=scammer_vendor")
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        
        results = search_response.data['results']
        self.assertEqual(len(results), 1)
        target_user_id = results[0]['id']
        self.assertEqual(results[0]['is_active'], True)

        # Step 2: Admin applies penalty (Suspension)
        try:
            suspend_url = reverse('accounts:admin-suspend-user', kwargs={'user_id': target_user_id})
        except:
            suspend_url = reverse('admin-suspend-user', kwargs={'user_id': target_user_id})
            
        penalty_payload = {"justification": "E2E Test: Defrauded buyer on contract #992."}
        suspend_response = self.client.post(suspend_url, penalty_payload)
        self.assertEqual(suspend_response.status_code, status.HTTP_200_OK)

        # Step 3: Verify the penalty was applied to the database
        self.fraudulent_vendor.refresh_from_db()
        self.assertFalse(self.fraudulent_vendor.is_active)

        # Step 4: Audit log created (The Immutable Proof)
        log = AdminAuditLog.objects.filter(object_id=target_user_id).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin, self.risk_admin)
        self.assertEqual(log.action_type, AdminActionType.SUSPEND_USER)
        self.assertEqual(log.justification, penalty_payload["justification"])