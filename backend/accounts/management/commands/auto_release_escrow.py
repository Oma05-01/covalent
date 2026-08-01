from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from accounts.models import Contract, Wallet # Adjust imports based on your exact app names

class Command(BaseCommand):
    help = 'Checks for expired inspection windows and auto-releases escrowed funds to vendors.'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        
        # 1. Find all contracts that are DELIVERED and past their timer
        expired_contracts = Contract.objects.filter(
            status='DELIVERED',
            auto_release_at__lte=now
        )
        
        if not expired_contracts.exists():
            self.stdout.write("No expired inspection windows found.")
            return

        success_count = 0

        for contract in expired_contracts:
            try:
                # 2. THE LOCK: transaction.atomic + select_for_update
                # This freezes the row. If a buyer is simultaneously trying to dispute, 
                # the database forces one action to wait for the other to finish.
                with transaction.atomic():
                    locked_contract = Contract.objects.select_for_update().get(contract_id=contract.contract_id)
                    
                    # 3. Double-check status inside the lock (in case it changed milliseconds ago)
                    if locked_contract.status != 'DELIVERED':
                        self.stdout.write(self.style.WARNING(f"Contract {locked_contract.contract_id} status changed. Skipping."))
                        continue
                        
                    # 4. Execute the Payout
                    vendor_wallet, _ = Wallet.objects.get_or_create(user__email=locked_contract.vendor_email)
                    
                    # Move funds from locked to available
                    vendor_wallet.locked_escrow_balance -= locked_contract.total_escrow
                    vendor_wallet.available_balance += locked_contract.total_escrow
                    vendor_wallet.save()
                    
                    # 5. Update Contract Status
                    locked_contract.status = 'RELEASED'
                    locked_contract.save()
                    
                    # Optional: Add your PlatformAuditLog creation here
                    
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Successfully auto-released ₦{locked_contract.total_escrow} for Contract {locked_contract.contract_id}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to process Contract {contract.contract_id}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"Worker finished. Processed {success_count} auto-releases."))