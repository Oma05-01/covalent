from django.test import TestCase
from django.contrib.auth import get_user_model
from governance.models import GovernanceProfile
from governance.risk_engine import RiskMitigationEngine

User = get_user_model()

class RiskEngineUnitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="target@example.com", password="pw")
        self.profile = self.user.governance_profile

    def test_clean_transaction_adds_no_risk(self):
        telemetry = {'sim_swap_detected': False, 'ip_geolocation_mismatch': False}
        profile, added_risk = RiskMitigationEngine.evaluate_transaction_risk(self.user, telemetry)
        
        self.assertEqual(added_risk, 0)
        self.assertEqual(profile.fraud_risk_score, 0)

    def test_moderate_threat_increases_fraud_score_silently(self):
        telemetry = {'ip_geolocation_mismatch': True, 'velocity_spike': True}
        profile, added_risk = RiskMitigationEngine.evaluate_transaction_risk(self.user, telemetry)
        
        self.assertEqual(added_risk, 35) # 20 + 15
        self.assertEqual(profile.fraud_risk_score, 35)
        # Status remains ACTIVE because it hasn't crossed the 100 threshold
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.ACTIVE)

    def test_critical_threat_triggers_immediate_suspension(self):
        # Simulating a severe account takeover attempt
        telemetry = {
            'sim_swap_detected': True, 
            'velocity_spike': True, 
            'failed_auth_burst': True
        }
        profile, added_risk = RiskMitigationEngine.evaluate_transaction_risk(self.user, telemetry)
        
        self.assertEqual(added_risk, 100) # 75 + 15 + 10
        self.assertEqual(profile.fraud_risk_score, 100)
        
        # The engine must prioritize platform security and lock the account
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.SUSPENDED)