from django.test import TestCase
from django.contrib.auth import get_user_model
from governance.models import GovernanceProfile, TrustLog
from governance.services import process_governance_event

User = get_user_model()

class GovernanceServiceUnitTests(TestCase):
    
    def setUp(self):
        self.user = User.objects.create_user(email="serviceuser@example.com", password="pw")
        self.profile = self.user.governance_profile

    def test_process_event_creates_log_and_updates_score(self):
        """A single event should adjust the score and create a TrustLog."""
        profile, log = process_governance_event(
            user=self.user,
            event_type=TrustLog.EventType.CONTRACT_SUCCESS,
            trust_impact=5,
            loyalty_impact=10,
            reference_id="CONT-123",
            description="Clean contract delivered."
        )
        
        self.assertEqual(profile.trust_score, 55)
        self.assertEqual(profile.loyalty_points, 10)
        self.assertEqual(TrustLog.objects.count(), 1)
        self.assertEqual(log.trust_impact, 5)

    def test_warning_engine_triggers_warning_status(self):
        """Dropping below 50 but above 24 triggers a WARNING status."""
        # Start at 50, drop 15 -> 35 (Should be WARNING)
        profile, _ = process_governance_event(
            user=self.user,
            event_type=TrustLog.EventType.DISPUTE_LOST,
            trust_impact=-15,
            description="Lost arbitration."
        )
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.WARNING)

    def test_warning_engine_triggers_restricted_status(self):
        """Dropping below 25 triggers a RESTRICTED status."""
        # Start at 50, drop 30 -> 20 (Should be RESTRICTED)
        profile, _ = process_governance_event(
            user=self.user,
            event_type=TrustLog.EventType.PLATFORM_VIOLATION,
            trust_impact=-30,
            description="Severe violation."
        )
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.RESTRICTED)

    def test_account_recovery_restores_active_status(self):
        """Gaining trust back above 50 restores ACTIVE status."""
        self.profile.trust_score = 20
        self.profile.status = GovernanceProfile.AccountStatus.RESTRICTED
        self.profile.save()

        # Gain 40 points -> 60 (Should be ACTIVE again)
        profile, _ = process_governance_event(
            user=self.user,
            event_type=TrustLog.EventType.MANUAL_ADJUSTMENT,
            trust_impact=40,
            description="Admin restored trust."
        )
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.ACTIVE)

    def test_fraud_score_is_isolated_from_public_trust(self):
        """Ensure standard governance events do not alter the internal fraud risk score."""
        initial_fraud_score = self.profile.fraud_risk_score
        
        # User loses a dispute (public penalty)
        process_governance_event(
            user=self.user,
            event_type=TrustLog.EventType.DISPUTE_LOST,
            trust_impact=-15,
            description="Lost dispute."
        )
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.trust_score, 35)
        # Fraud score must remain completely untouched
        self.assertEqual(self.profile.fraud_risk_score, initial_fraud_score)