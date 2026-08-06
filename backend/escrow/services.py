from decimal import Decimal, ROUND_DOWN
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from accounts.models import PlatformAuditLog
from .models import Wallet, LedgerTransaction
from django.core.exceptions import ValidationError
from governance.services import process_governance_event
from governance.models import TrustLog

@transaction.atomic
def execute_dispute_consensus(dispute):
    votes = dispute.votes.all() 
    
    if votes.count() < 3:
        return False, "Awaiting remaining votes."

    buyer_votes = votes.filter(ruling='buyer').count()
    vendor_votes = votes.filter(ruling='vendor').count()
    
    winner = 'buyer' if buyer_votes >= 2 else 'vendor'
    
    contract = dispute.contract
    escrow_amount = contract.total_escrow
    TRUST_SCORE_PENALTY = -15 # Severe penalty for losing arbitration
    TRUST_SCORE_BUMP = 2      # Small reward for being in the right

    # Execute Payout & Apply Penalties
    if winner == 'buyer':
        # Buyer was right. Refund Buyer, Penalize Vendor.
        wallet = contract.creator.wallet
        wallet.available_balance += escrow_amount
        wallet.save()
        contract.status = 'REFUNDED'
        
        # 🆕 Apply Governance updates via the Service Layer
        process_governance_event(
            user=contract.vendor,
            event_type=TrustLog.EventType.DISPUTE_LOST,
            trust_impact=TRUST_SCORE_PENALTY,
            reference_id=dispute.id,
            description=f"Lost dispute #{dispute.id} as Vendor."
        )
        process_governance_event(
            user=contract.creator,
            event_type=TrustLog.EventType.DISPUTE_WON,
            trust_impact=TRUST_SCORE_BUMP,
            reference_id=dispute.id,
            description=f"Won dispute #{dispute.id} as Buyer."
        )
        
    else:
        # Vendor was right. Pay Vendor, Penalize Buyer for false dispute.
        wallet = contract.vendor.wallet
        wallet.available_balance += escrow_amount
        wallet.save()
        contract.status = 'COMPLETED'
        
        # 🆕 Apply Governance updates via the Service Layer
        process_governance_event(
            user=contract.creator,
            event_type=TrustLog.EventType.DISPUTE_LOST,
            trust_impact=TRUST_SCORE_PENALTY,
            reference_id=dispute.id,
            description=f"Lost dispute #{dispute.id} as Buyer (False Claim)."
        )
        process_governance_event(
            user=contract.vendor,
            event_type=TrustLog.EventType.DISPUTE_WON,
            trust_impact=TRUST_SCORE_BUMP,
            reference_id=dispute.id,
            description=f"Won dispute #{dispute.id} as Vendor."
        )

    # Distribute Arbitration Fees to Lawyers
    TOTAL_FEE = Decimal('5000.00')
    LAWYER_CUT = (TOTAL_FEE / Decimal('3.00')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)

    for vote in votes:
        lawyer_wallet = vote.lawyer.wallet
        lawyer_wallet.available_balance += LAWYER_CUT
        lawyer_wallet.save()

    # Finalize the Records
    contract.save()
    dispute.status = 'RESOLVED'
    dispute.save()

    return True, f"Consensus reached. {winner.upper()} won. Funds disbursed and penalties applied."

@transaction.atomic
def deposit_funds(user, amount, reference=None):
    """Adds funds to the user's available balance."""
    wallet = Wallet.objects.select_for_update().get(user=user)
    wallet.available_balance += amount
    wallet.save()
    
    tx = LedgerTransaction.objects.create(
        wallet=wallet, 
        amount=amount, 
        transaction_type="DEPOSIT", 
        reference=reference
    )
    return wallet, tx

@transaction.atomic
def withdraw_funds(user, amount):
    """Removes funds from available balance, strictly preventing overdrafts."""
    wallet = Wallet.objects.select_for_update().get(user=user)
    
    if wallet.available_balance < amount:
        raise ValidationError("Insufficient available funds.")
        
    wallet.available_balance -= amount
    wallet.save()
    
    tx = LedgerTransaction.objects.create(
        wallet=wallet, 
        amount=amount, 
        transaction_type="WITHDRAWAL"
    )
    return wallet, tx

@transaction.atomic
def lock_escrow(user, amount, reference=None):
    """Moves funds from available to locked status."""
    wallet = Wallet.objects.select_for_update().get(user=user)
    
    if wallet.available_balance < amount:
        raise ValidationError("Insufficient available funds for escrow.")
        
    wallet.available_balance -= amount
    wallet.locked_escrow_balance += amount  # 👈 Updated!
    wallet.save()
    
    tx = LedgerTransaction.objects.create(
        wallet=wallet, 
        amount=amount, 
        transaction_type="ESCROW_LOCK", 
        reference=reference
    )
    return wallet, tx

@transaction.atomic
def release_escrow(buyer, vendor, amount, reference=None):
    """Releases locked buyer funds into the vendor's available balance and applies governance rewards."""
    buyer_wallet = Wallet.objects.select_for_update().get(user=buyer)
    vendor_wallet = Wallet.objects.select_for_update().get(user=vendor)
    
    if buyer_wallet.locked_escrow_balance < amount:  # 👈 Updated!
        raise ValidationError("Insufficient locked funds for release.")
        
    # Deduct from buyer's lock
    buyer_wallet.locked_escrow_balance -= amount  # 👈 Updated!
    buyer_wallet.save()
    
    # Add to vendor's available
    vendor_wallet.available_balance += amount
    vendor_wallet.save()
    
    # Log both sides of the transaction
    tx_debit = LedgerTransaction.objects.create(
        wallet=buyer_wallet, amount=amount, transaction_type="ESCROW_RELEASE", 
        reference=f"{reference}_deb" if reference else None
    )
    tx_credit = LedgerTransaction.objects.create(
        wallet=vendor_wallet, amount=amount, transaction_type="DEPOSIT", 
        reference=f"{reference}_cred" if reference else None
    )
    
    # 👇 NEW: Reward both parties for a clean, successful transaction
    # We use the transaction reference (typically the contract_id) as the reference_id
    process_governance_event(
        user=vendor,
        event_type=TrustLog.EventType.CONTRACT_SUCCESS,
        trust_impact=5,      # Vendor gets a solid trust bump for delivering successfully
        loyalty_impact=10,   # Loyalty points for platform usage
        reference_id=reference if reference else "",
        description="Successfully delivered and released contract."
    )

    process_governance_event(
        user=buyer,
        event_type=TrustLog.EventType.CONTRACT_SUCCESS,
        trust_impact=2,      # Buyer gets a smaller trust bump for a smooth transaction
        loyalty_impact=10,   # Loyalty points for platform usage
        reference_id=reference if reference else "",
        description="Successfully completed contract as Buyer."
    )
    
    return buyer_wallet, vendor_wallet, [tx_debit, tx_credit]


def mark_contract_delivered(contract, vendor):
    """Marks work delivered, sets inspection timer, and enforces contract immutability."""
    if contract.vendor != vendor:
        raise ValidationError("Only the assigned vendor can mark this contract as delivered.")
    
    if contract.status not in ["FUNDED"]:
        raise ValidationError("Only funded contracts can be marked as delivered.")

    # Business Rule: Delivered contracts become immutable regarding core terms
    contract.status = "DELIVERED"
    contract.delivered_at = timezone.now()
    
    # Set inspection period timer (e.g., default 72 hours or contract defined)
    hours = contract.inspection_period_hours or 72
    contract.auto_release_at = contract.delivered_at + timedelta(hours=hours)
    contract.save()
    return contract