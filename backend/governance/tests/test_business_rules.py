from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import serializers
from governance.models import GovernanceProfile
from governance.risk_engine import RiskMitigationEngine

User = get_user_model()

# We define a mock serializer here to represent your public-facing API.
# If you already have a GovernanceProfileSerializer, you can import and test that instead!
class PublicGovernanceProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = GovernanceProfile
        # The critical business rule: fraud_risk_score must NEVER be in this list
        fields = ['status', 'id'] 

class BusinessRuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="pw")
        self.profile = self.user.governance_profile

    def test_fraud_score_remains_private(self):
        """
        Business Rule: The internal fraud score must never be exposed 
        to the client-side application.
        """
        self.profile.fraud_risk_score = 45
        self.profile.save()

        # Serialize the profile as it would be sent to the frontend
        serializer = PublicGovernanceProfileSerializer(self.profile)
        data = serializer.data

        # Assert the score is completely hidden from the payload
        self.assertNotIn('fraud_risk_score', data)
        self.assertIn('status', data)

    def test_restrictions_proportional_to_risk(self):
        """
        Business Rule: 
        Risk >= 70 triggers RESTRICTED (can browse, but limited actions).
        Risk >= 100 triggers SUSPENDED (completely locked out).
        """
        # 1. Test 70 threshold (Restricted)
        # We pass a threat worth 75 points ('sim_swap_detected')
        updated_profile, _ = RiskMitigationEngine.evaluate_transaction_risk(
            self.user, 
            telemetry_data={'sim_swap_detected': True}
        )
        self.assertEqual(updated_profile.status, GovernanceProfile.AccountStatus.RESTRICTED)

        # 2. Test 100 threshold (Suspended)
        # We pass additional threats worth 35 points (Total score becomes 75 + 35 = 110)
        updated_profile, _ = RiskMitigationEngine.evaluate_transaction_risk(
            self.user, 
            telemetry_data={
                'ip_geolocation_mismatch': True,  # 20 points
                'velocity_spike': True            # 15 points
            }
        )
        self.assertEqual(updated_profile.status, GovernanceProfile.AccountStatus.SUSPENDED)
        
    def test_admin_can_override_false_positives(self):
        """
        Business Rule: If the engine suspends a user, an admin must be able 
        to manually clear their score and restore their account.
        """
        # 1. System suspends the user
        self.profile.fraud_risk_score = 150
        self.profile.status = GovernanceProfile.AccountStatus.SUSPENDED
        self.profile.save()

        # 2. Admin reviews the case, determines it's a false positive, and resets the account
        self.profile.fraud_risk_score = 0
        self.profile.status = GovernanceProfile.AccountStatus.ACTIVE
        self.profile.save()

        # 3. User makes a clean transaction
        updated_profile, risk_added = RiskMitigationEngine.evaluate_transaction_risk(self.user, {})

        # 4. Assert the user remains active and is not immediately re-suspended
        self.assertEqual(risk_added, 0)
        self.assertEqual(updated_profile.status, GovernanceProfile.AccountStatus.ACTIVE)
        self.assertEqual(updated_profile.fraud_risk_score, 0)