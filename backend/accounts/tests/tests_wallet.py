from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal

# Pull Wallet from accounts, but Ledger & Services from escrow!
from accounts.models import Wallet
from escrow.models import LedgerTransaction
from escrow.services import deposit_funds, withdraw_funds, lock_escrow, release_escrow

User = get_user_model()

class WalletAndEscrowTests(TestCase):
    def setUp(self):
        """Provision users and fetch their auto-provisioned wallets."""
        self.buyer = User.objects.create_user(
            email="fund_buyer@covalent.com", password="securepassword123"
        )
        self.vendor = User.objects.create_user(
            email="fund_vendor@covalent.com", password="securepassword123"
        )
        
        # Assuming Phase A auto-provisions wallets on user creation
        self.buyer_wallet = Wallet.objects.get(user=self.buyer)
        self.vendor_wallet = Wallet.objects.get(user=self.vendor)

    def test_deposit_and_ledger_entry(self):
        """Asserts deposits increase available balance and create a ledger entry."""
        wallet, transaction = deposit_funds(self.buyer, Decimal("50000.00"), reference="DEP_123")
        
        self.assertEqual(wallet.available_balance, Decimal("50000.00"))
        self.assertEqual(wallet.locked_escrow_balance, Decimal("0.00"))
        self.assertEqual(transaction.transaction_type, "DEPOSIT")
        self.assertEqual(transaction.amount, Decimal("50000.00"))

    def test_withdraw_funds_and_limits(self):
        """Asserts users can withdraw, but not more than their available balance."""
        deposit_funds(self.buyer, Decimal("50000.00"), reference="DEP_124")
        
        # Successful withdrawal
        wallet, tx = withdraw_funds(self.buyer, Decimal("20000.00"))
        self.assertEqual(wallet.available_balance, Decimal("30000.00"))
        self.assertEqual(tx.transaction_type, "WITHDRAWAL")
        
        # Overdraft prevention
        with self.assertRaisesMessage(ValidationError, "Insufficient available funds."):
            withdraw_funds(self.buyer, Decimal("40000.00"))

    def test_lock_funds_in_escrow(self):
        """Asserts locking funds moves money from available to locked."""
        deposit_funds(self.buyer, Decimal("100000.00"), reference="DEP_125")
        
        wallet, tx = lock_escrow(self.buyer, Decimal("40000.00"), reference="ESC_LOCK_01")
        
        self.assertEqual(wallet.available_balance, Decimal("60000.00"))
        self.assertEqual(wallet.locked_escrow_balance, Decimal("40000.00"))
        self.assertEqual(tx.transaction_type, "ESCROW_LOCK")

    def test_cannot_withdraw_locked_funds(self):
        """Asserts locked funds are completely fenced off from withdrawals."""
        deposit_funds(self.buyer, Decimal("50000.00"), reference="DEP_126")
        lock_escrow(self.buyer, Decimal("50000.00"), reference="ESC_LOCK_02")
        
        # Wallet has 50k total, but 0 available
        with self.assertRaisesMessage(ValidationError, "Insufficient available funds."):
            withdraw_funds(self.buyer, Decimal("10000.00"))

    def test_escrow_never_negative(self):
        """Asserts we can never lock more money than the user actually has."""
        deposit_funds(self.buyer, Decimal("10000.00"), reference="DEP_127")
        
        with self.assertRaisesMessage(ValidationError, "Insufficient available funds for escrow."):
            lock_escrow(self.buyer, Decimal("15000.00"), reference="ESC_LOCK_03")

    def test_release_escrow_to_vendor(self):
        """Asserts releasing escrow deducts from buyer's locked and adds to vendor's available."""
        deposit_funds(self.buyer, Decimal("100000.00"), reference="DEP_128")
        lock_escrow(self.buyer, Decimal("100000.00"), reference="ESC_LOCK_04")
        
        # Action: Release funds
        buyer_wallet, vendor_wallet, txs = release_escrow(
            buyer=self.buyer, 
            vendor=self.vendor, 
            amount=Decimal("100000.00"),
            reference="ESC_RELEASE_01"
        )
        
        # Buyer should have 0 locked, 0 available
        self.assertEqual(buyer_wallet.locked_escrow_balance, Decimal("0.00"))
        self.assertEqual(buyer_wallet.available_balance, Decimal("0.00"))
        
        # Vendor should have 100k available
        self.assertEqual(vendor_wallet.available_balance, Decimal("100000.00"))
        
        # We should have two ledger entries (one debit, one credit)
        self.assertEqual(len(txs), 2)