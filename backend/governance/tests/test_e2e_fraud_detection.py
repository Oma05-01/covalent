import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import Contract
from governance.models import GovernanceProfile
from governance.risk_engine import RiskMitigationEngine
from notifications.models import Notification

User = get_user_model()

class E2EFraudDetectionTests(TestCase):
    def setUp(self):
        self.scammer = User.objects.create_user(email="scammer@example.com", password="pw")
        self.vendor = User.objects.create_user(
            email="vendor@example.com", 
            password="pw",
            paystack_subaccount_code="ACCT_mock_456"
        )

    def _create_contract(self, status='PENDING'):
        """Helper to simulate contract creation over time."""
        return Contract.objects.create(
            contract_id=uuid.uuid4(),
            creator=self.scammer,
            vendor_email=self.vendor.email,
            item_amount="150.00",
            delivery_fee="15.00",
            status=status
        )

    def test_full_fraud_lifecycle_and_suspension(self):
        """
        E2E Flow:
        Create suspicious behavior -> Fraud score increases -> Restrictions applied -> Notification sent
        """
        # 1. Baseline: Account is Active, Score is 0
        profile = self.scammer.governance_profile
        self.assertEqual(profile.status, GovernanceProfile.AccountStatus.ACTIVE)
        self.assertEqual(profile.fraud_risk_score, 0)

        # 2. Suspicious Behavior: Scammer spams 11 contracts to launder money,
        # and disputes 9 of them to scam the vendors.
        for _ in range(2):
            self._create_contract(status='COMPLETED')
        for _ in range(9):
            self._create_contract(status='DISPUTED')

        # 3. Telemetry Trigger: Scammer tries to make one more transaction while using a VPN
        telemetry = {
            'ip_geolocation_mismatch': True,  # Adds +20 risk
            'velocity_spike': False
        }

        # 4. Action: The Engine evaluates the new transaction request
        updated_profile, risk_added = RiskMitigationEngine.evaluate_transaction_risk(
            user=self.scammer,
            telemetry_data=telemetry
        )

        # 5. Verify: Fraud Score Increases
        # Math: +25 (Spam Volume) + 60 (Critical Dispute Ratio) + 20 (IP Mismatch) = 105
        self.assertEqual(risk_added, 105)
        self.assertEqual(updated_profile.fraud_risk_score, 105)

        # 6. Verify: Restrictions Applied (Silent Kill-Switch activated)
        self.assertEqual(updated_profile.status, GovernanceProfile.AccountStatus.SUSPENDED)

        # 7. Verify: Notification System triggered successfully
        notifications = Notification.objects.filter(user=self.scammer)
        self.assertEqual(notifications.count(), 1)
        
        suspension_alert = notifications.first()
        self.assertEqual(suspension_alert.notification_type, Notification.NotificationType.SECURITY_ALERT)
        self.assertEqual(suspension_alert.title, "Account Suspended")