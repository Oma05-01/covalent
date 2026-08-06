from django.test import TestCase
from django.contrib.auth import get_user_model
from governance.models import GovernanceProfile, TrustLog
from governance.services import process_governance_event

User = get_user_model()

class BadActorPipelineE2ETests(TestCase):
    def setUp(self):
        # We start with a fresh, seemingly innocent user
        self.bad_actor = User.objects.create_user(email="scammer@example.com", password="password")

    def test_progressive_account_degradation(self):
        """
        E2E: Simulates a user consistently acting in bad faith over time,
        triggering automated downgrades from ACTIVE -> WARNING -> RESTRICTED.
        """
        profile = self.bad_actor.governance_profile
        
        # 1. Baseline: User starts with a clean slate
        self.assertEqual(profile.trust_score, 50)
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.ACTIVE)

        # 2. Strike 1: Loses their first dispute
        process_governance_event(
            user=self.bad_actor,
            event_type=TrustLog.EventType.DISPUTE_LOST,
            trust_impact=-15,
            description="Lost dispute #1 - Faulty goods."
        )
        profile.refresh_from_db()
        
        # Score drops to 35. Engine should automatically flag them as WARNING.
        self.assertEqual(profile.trust_score, 35)
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.WARNING)
        
        # 3. Strike 2: Loses another dispute
        process_governance_event(
            user=self.bad_actor,
            event_type=TrustLog.EventType.DISPUTE_LOST,
            trust_impact=-15,
            description="Lost dispute #2 - Non-delivery."
        )
        profile.refresh_from_db()
        
        # Score drops to 20. Engine should automatically restrict them.
        self.assertEqual(profile.trust_score, 20)
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.RESTRICTED)

        # 4. Strike 3: Severe TOS Violation
        process_governance_event(
            user=self.bad_actor,
            event_type=TrustLog.EventType.PLATFORM_VIOLATION,
            trust_impact=-30,
            description="Attempted to bypass platform fees."
        )
        profile.refresh_from_db()
        
        # Score hits the floor (0) but does not go negative. 
        self.assertEqual(profile.trust_score, 0)
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.RESTRICTED)

        # 5. Manual Intervention: Admin permanently suspends the account
        profile.status = GovernanceProfile.AccountStatus.SUSPENDED
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.SUSPENDED)
        
        # 6. Verify the Immutable Ledger
        # If the user complains, customer support can instantly pull this exact history
        logs = profile.logs.all().order_by('created_at')
        self.assertEqual(logs.count(), 3)
        self.assertEqual(logs[0].trust_impact, -15)
        self.assertEqual(logs[1].trust_impact, -15)
        self.assertEqual(logs[2].trust_impact, -30)