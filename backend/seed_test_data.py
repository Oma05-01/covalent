import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import CovalentUser, Wallet

def seed_data():
    print("🌱 Starting database seeding...")

    # 1. Create Lawyer
    lawyer, _ = CovalentUser.objects.get_or_create(
        email="lawyer@covalent.ng",
        defaults={
            "first_name": "Barrister",
            "last_name": "Adeyemi",
            "is_lawyer": True,
            "is_kyc_verified": True,
            "trust_score": 98
        }
    )
    lawyer.set_password("Lawyer123!")
    lawyer.save()
    Wallet.objects.get_or_create(user=lawyer)
    print("✔ Lawyer ready: lawyer@covalent.ng / Lawyer123!")

    # 2. Create Buyer (With ₦5,000,000 wallet balance)
    buyer, _ = CovalentUser.objects.get_or_create(
        email="buyer@covalent.ng",
        defaults={
            "first_name": "Chidi",
            "last_name": "Okafor",
            "is_kyc_verified": True,
            "trust_score": 85
        }
    )
    buyer.set_password("Buyer123!")
    buyer.save()
    
    buyer_wallet, _ = Wallet.objects.get_or_create(user=buyer)
    buyer_wallet.available_balance = 5000000.00
    buyer_wallet.save()
    print("✔ Buyer ready: buyer@covalent.ng / Buyer123! (₦5M Balance)")

    # 3. Create Vendor (With linked settlement account)
    vendor, _ = CovalentUser.objects.get_or_create(
        email="vendor@covalent.ng",
        defaults={
            "first_name": "Tunde",
            "last_name": "Bakare",
            "is_kyc_verified": True,
            "trust_score": 92,
            "bank_name": "Guaranty Trust Bank (GTB)",
            "account_number": "0123456789",
            "account_name": "Tunde Bakare",
            "paystack_subaccount_code": "ACCT_mock_vendor_123"  # <-- Added here!
        }
    )
    vendor.set_password("Vendor123!")
    vendor.bank_name = "Guaranty Trust Bank (GTB)"
    vendor.account_number = "0123456789"
    vendor.account_name = "Tunde Bakare"
    vendor.paystack_subaccount_code = "ACCT_mock_vendor_123"  # <-- And forced here!
    vendor.save()

    Wallet.objects.get_or_create(user=vendor)
    print("✔ Vendor ready: vendor@covalent.ng / Vendor123! (GTB Bank Linked)")
    
    print("\n✨ Seeding complete! You can now run the end-to-end lifecycle.")

if __name__ == '__main__':
    seed_data()