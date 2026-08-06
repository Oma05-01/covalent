import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Contract  # Adjust if your Contract is in the escrow app
from governance.pattern_detection import PatternAnalyzer
from governance.risk_engine import RiskMitigationEngine
from governance.models import GovernanceProfile

User = get_user_model()

class PatternDetectionIntegrationTests(TestCase):
    def setUp(self):
        self.attacker = User.objects.create_user(email="attacker@example.com", password="pw")
        self.vendor = User.objects.create_user(
            email="vendor@example.com", 
            password="pw",
            paystack_subaccount_code="ACCT_mock_123"
        )
        
    def _create_contracts(self, count, status='PENDING'):
        """Helper to rapidly generate dummy contracts for the attacker."""
        for _ in range(count):
            Contract.objects.create(
                contract_id=uuid.uuid4(),
                creator=self.attacker,
                vendor_email=self.vendor.email,
                item_amount="100.00",
                delivery_fee="10.00",
                status=status
            )

    def test_clean_user_gets_zero_penalty(self):
        """A user with a normal contract history should receive 0 risk points."""
        self._create_contracts(2, status='COMPLETED')
        
        penalty = PatternAnalyzer.evaluate_all_patterns(self.attacker)
        self.assertEqual(penalty, 0)

    def test_high_dispute_ratio_triggers_penalty(self):
        """If >50% of contracts are disputed (min 3 total), apply +30 penalty."""
        # 5 total contracts, 3 disputed = 60% dispute ratio
        self._create_contracts(2, status='COMPLETED')
        self._create_contracts(3, status='DISPUTED')
        
        penalty = PatternAnalyzer.analyze_dispute_patterns(self.attacker)
        self.assertEqual(penalty, 30)

    def test_critical_dispute_ratio_triggers_max_penalty(self):
        """If >75% of contracts are disputed, apply +60 penalty."""
        # 5 total contracts, 4 disputed = 80% dispute ratio
        self._create_contracts(1, status='COMPLETED')
        self._create_contracts(4, status='DISPUTED')
        
        penalty = PatternAnalyzer.analyze_dispute_patterns(self.attacker)
        self.assertEqual(penalty, 60)

    def test_spam_contract_creation_triggers_penalty(self):
        """Creating more than 10 contracts in 24 hours flags as suspicious (+25)."""
        self._create_contracts(11, status='PENDING')
        
        penalty = PatternAnalyzer.analyze_suspicious_contracts(self.attacker)
        self.assertEqual(penalty, 25)

    def test_engine_combines_patterns_and_suspends_user(self):
        """
        Integration test: The RiskMitigationEngine should read the patterns, 
        add them up, and trigger an account suspension if the threshold is crossed.
        """
        # Setup: 12 total contracts, 10 are disputed
        # Triggers Spam Penalty (+25) AND Critical Dispute Penalty (+60) = 85 risk points
        self._create_contracts(2, status='COMPLETED')
        self._create_contracts(10, status='DISPUTED')
        
        # Add a minor telemetry flag to push it over 100
        # 85 (Pattern) + 20 (IP Mismatch) = 105
        telemetry = {
            'ip_geolocation_mismatch': True,
            'velocity_spike': False
        }
        
        # Action: Evaluate transaction
        profile, risk_added = RiskMitigationEngine.evaluate_transaction_risk(
            user=self.attacker, 
            telemetry_data=telemetry
        )
        
        # Assertions
        self.assertEqual(risk_added, 105)
        profile.refresh_from_db()
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.SUSPENDED)