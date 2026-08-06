from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from governance.models import GovernanceProfile, DeviceFingerprint
from governance.device_tracking import DeviceTracker
from governance.risk_engine import RiskMitigationEngine

User = get_user_model()

class DeviceTrackingTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.scammer = User.objects.create_user(email="scammer@example.com", password="pw")
        self.new_account = User.objects.create_user(email="newguy@example.com", password="pw")
        self.innocent = User.objects.create_user(email="innocent@example.com", password="pw")

    def _create_mock_request(self, ip, user_agent):
        """Helper to simulate an incoming HTTP request with specific headers."""
        request = self.factory.get('/api/v1/escrow/contracts/')
        request.META['REMOTE_ADDR'] = ip
        request.META['HTTP_USER_AGENT'] = user_agent
        return request

    def test_device_matching_generates_consistent_hash(self):
        """Unit Test: The same IP and User-Agent must always yield the same hash."""
        hash1 = DeviceFingerprint.generate_hash('192.168.1.1', 'Mozilla/5.0')
        hash2 = DeviceFingerprint.generate_hash('192.168.1.1', 'Mozilla/5.0')
        hash3 = DeviceFingerprint.generate_hash('10.0.0.1', 'Mozilla/5.0')
        
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)

    def test_repeat_account_detection_flags_evasion(self):
        """Integration Test: A new account on a suspended user's device triggers ban evasion."""
        # 1. Scammer makes a request and gets their device fingerprinted
        scammer_request = self._create_mock_request('203.0.113.50', 'Chrome/100.0')
        DeviceTracker.process_and_check_evasion(self.scammer, scammer_request)
        
        # 2. Scammer gets suspended by the system
        scammer_profile = self.scammer.governance_profile
        scammer_profile.status = GovernanceProfile.AccountStatus.SUSPENDED
        scammer_profile.save()

        # 3. Scammer creates 'new_account' and logs in on the EXACT SAME device
        new_account_request = self._create_mock_request('203.0.113.50', 'Chrome/100.0')
        
        # Action: Evaluate risk for the new account
        profile, risk_added = RiskMitigationEngine.evaluate_transaction_risk(
            user=self.new_account,
            telemetry_data={},
            request=new_account_request
        )

        # Assertions: The new account should be instantly hit with 100 points and suspended
        self.assertEqual(risk_added, 100)
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.SUSPENDED)

    def test_clean_shared_device_is_safe(self):
        """Integration Test: Two users sharing a device is fine as long as neither is suspended."""
        req1 = self._create_mock_request('198.51.100.10', 'Safari/15.0')
        req2 = self._create_mock_request('198.51.100.10', 'Safari/15.0')

        # User 1 uses the device
        DeviceTracker.process_and_check_evasion(self.innocent, req1)
        
        # User 2 uses the same device
        profile, risk_added = RiskMitigationEngine.evaluate_transaction_risk(
            user=self.new_account,
            telemetry_data={},
            request=req2
        )

        # No penalty should be applied
        self.assertEqual(risk_added, 0)
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.ACTIVE)