from decimal import Decimal, ROUND_DOWN
from django.db import transaction
from accounts.models import PlatformAuditLog

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
    TRUST_SCORE_PENALTY = 15 # Severe penalty for losing arbitration

    # Execute Payout & Apply Penalties
    if winner == 'buyer':
        # Buyer was right. Refund Buyer, Penalize Vendor.
        wallet = contract.buyer.wallet
        wallet.available_balance += escrow_amount
        wallet.save()
        contract.status = 'REFUNDED'
        
        # 🆕 Apply the Vendor Penalty
        contract.vendor.trust_score -= TRUST_SCORE_PENALTY
        contract.vendor.save()
        
        PlatformAuditLog.objects.create(
            user=contract.vendor,
            action_type="TRUST_SCORE_SLASHED",
            description=f"Lost dispute #{dispute.id}. Deducted {TRUST_SCORE_PENALTY} points."
        )
        
    else:
        # Vendor was right. Pay Vendor, Penalize Buyer for false dispute.
        wallet = contract.vendor.wallet
        wallet.available_balance += escrow_amount
        wallet.save()
        contract.status = 'COMPLETED'
        
        # 🆕 Apply the Buyer Penalty
        contract.buyer.trust_score -= TRUST_SCORE_PENALTY
        contract.buyer.save()
        
        PlatformAuditLog.objects.create(
            user=contract.buyer,
            action_type="TRUST_SCORE_SLASHED",
            description=f"Lost dispute #{dispute.id} (False Claim). Deducted {TRUST_SCORE_PENALTY} points."
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