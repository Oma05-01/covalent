from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from escrow.services import release_escrow
from accounts.models import Wallet

User = get_user_model()

class EscrowGovernanceIntegrationTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(email="buyer@example.com", password="pw")
        self.vendor = User.objects.create_user(email="vendor@example.com", password="pw")
        
        # Setup Wallets
        self.buyer_wallet, _ = Wallet.objects.get_or_create(user=self.buyer)
        self.buyer_wallet.locked_escrow_balance = Decimal("1000.00")
        self.buyer_wallet.save()
        
        self.vendor_wallet, _ = Wallet.objects.get_or_create(user=self.vendor)
        self.vendor_wallet.available_balance = Decimal("0.00")
        self.vendor_wallet.save()

    def test_release_escrow_improves_trust_and_loyalty(self):
        """Integration: Releasing funds rewards both buyer and vendor."""
        
        # Verify initial states
        self.assertEqual(self.buyer.governance_profile.trust_score, 50)
        self.assertEqual(self.vendor.governance_profile.trust_score, 50)
        self.assertEqual(self.buyer.governance_profile.loyalty_points, 0)

        # Release the funds
        release_escrow(self.buyer, self.vendor, Decimal("1000.00"), reference="CONT-777")
        
        # Refresh profiles from DB
        self.buyer.governance_profile.refresh_from_db()
        self.vendor.governance_profile.refresh_from_db()
        
        # Verify Vendor rewards (+5 Trust, +10 Loyalty)
        self.assertEqual(self.vendor.governance_profile.trust_score, 55)
        self.assertEqual(self.vendor.governance_profile.loyalty_points, 10)
        
        # Verify Buyer rewards (+2 Trust, +10 Loyalty)
        self.assertEqual(self.buyer.governance_profile.trust_score, 52)
        self.assertEqual(self.buyer.governance_profile.loyalty_points, 10)

        # Verify wallet balances moved correctly
        self.buyer_wallet.refresh_from_db()
        self.vendor_wallet.refresh_from_db()
        self.assertEqual(self.buyer_wallet.locked_escrow_balance, Decimal("0.00"))
        self.assertEqual(self.vendor_wallet.available_balance, Decimal("1000.00"))