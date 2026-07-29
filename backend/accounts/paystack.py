import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

class PaystackService:
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def get_nigerian_banks(self):
        try:
            response = requests.get(
                f"{self.BASE_URL}/bank?country=nigeria", 
                headers=self.headers, 
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get("data", [])
        # Catch ALL errors (DNS, socket, timeout, offline) so it never throws a 500!
        except Exception as e:
            print(f"Paystack Network Error ({type(e).__name__}): Serving offline fallback banks.")
            
        return [
            {"name": "Access Bank", "code": "044"},
            {"name": "Guaranty Trust Bank (GTB)", "code": "058"},
            {"name": "Zenith Bank", "code": "057"},
            {"name": "United Bank for Africa (UBA)", "code": "033"},
            {"name": "Kuda Bank", "code": "50211"},
            {"name": "Opay Digital Services", "code": "999992"},
            {"name": "Moniepoint Microfinance Bank", "code": "50515"},
        ]

    def resolve_account_number(self, account_number, bank_code):
        """Validates that a 10-digit NUBAN matches a real Nigerian bank account name."""
        url = f"{self.BASE_URL}/bank/resolve?account_number={account_number}&bank_code={bank_code}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json().get("data", {})
        raise ValidationError("Invalid account number or bank code. Please check and try again.")

    def create_subaccount(self, user, bank_code, account_number, account_name):
        """Creates a Paystack subaccount for automated split payouts."""
        payload = {
            "business_name": account_name or str(user.get_full_name()),
            "settlement_bank": bank_code,
            "account_number": account_number,
            "percentage_charge": 5.0, # Example: Covalent takes 5% platform commission
            "description": f"Covalent Escrow Subaccount for {user.email}"
        }
        response = requests.post(f"{self.BASE_URL}/subaccount", json=payload, headers=self.headers)
        if response.status_code in [200, 201]:
            data = response.json().get("data", {})
            return data.get("subaccount_code")
        raise ValidationError("Failed to generate virtual subaccount with Paystack.")