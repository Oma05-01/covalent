from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from accounts.models import Contract  # Adjust import based on your exact structure

class PatternAnalyzer:
    """
    Analyzes historical database records to identify fraudulent patterns.
    Returns a calculated risk penalty based on detected anomalies.
    """

    @staticmethod
    def analyze_dispute_patterns(user) -> int:
        """
        Detects fake dispute patterns.
        If a user has a high ratio of disputed contracts vs total contracts, 
        they get heavily penalized.
        """
        risk_penalty = 0
        
        # Get user's contracts as a buyer
        stats = Contract.objects.filter(creator=user).aggregate(
            total=Count('pk'),
            disputed=Count('pk', filter=Q(status='DISPUTED'))
        )
        
        total_contracts = stats['total']
        disputed_contracts = stats['disputed']

        if total_contracts >= 3:
            dispute_ratio = disputed_contracts / total_contracts
            
            if dispute_ratio > 0.75:
                risk_penalty += 60  # Critical: 75%+ of contracts are disputed
            elif dispute_ratio > 0.50:
                risk_penalty += 30  # High: Half of contracts are disputed
                
        return risk_penalty

    @staticmethod
    def analyze_suspicious_contracts(user) -> int:
        """
        Detects multiple suspicious contracts (e.g., rapid creation of 
        identical amounts, or ping-ponging funds with the same vendor).
        """
        risk_penalty = 0
        twenty_four_hours_ago = timezone.now() - timedelta(days=1)

        # Count contracts created in the last 24 hours
        recent_contracts = Contract.objects.filter(
            creator=user,
            created_at__gte=twenty_four_hours_ago
        ).count()

        if recent_contracts > 10:
            risk_penalty += 25  # High volume in a short time (Money laundering risk)

        return risk_penalty

    @classmethod
    def evaluate_all_patterns(cls, user) -> int:
        """Runs all pattern checks and returns the total risk penalty."""
        total_penalty = 0
        total_penalty += cls.analyze_dispute_patterns(user)
        total_penalty += cls.analyze_suspicious_contracts(user)
        return total_penalty