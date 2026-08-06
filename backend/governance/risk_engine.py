from django.db import transaction
from .models import GovernanceProfile
from .device_tracking import DeviceTracker
import logging
from notifications.models import Notification
from .pattern_detection import PatternAnalyzer

logger = logging.getLogger(__name__)

class RiskMitigationEngine:
    """
    Evaluates real-time transactional threats and historical patterns. 
    Operates strictly on the internal fraud_risk_score.
    """
    
    # Define risk weights for specific threat vectors
    THREAT_MATRIX = {
        'sim_swap_detected': 75,
        'ip_geolocation_mismatch': 20,
        'velocity_spike': 15,
        'failed_auth_burst': 10,
        'ban_evasion_detected': 100
    }

    @classmethod
    @transaction.atomic
    def evaluate_transaction_risk(cls, user, telemetry_data, request=None):
        """
        Parses telemetry data and historical patterns to apply risk points. 
        If fraud risk exceeds 100, the account is immediately locked.
        """
        profile = user.governance_profile
        initial_status = profile.status
        total_risk_incurred = 0

        if request and DeviceTracker.process_and_check_evasion(user, request):
                telemetry_data['ban_evasion_detected'] = True

        # 1. Real-time Telemetry Risk
        for vector, weight in cls.THREAT_MATRIX.items():
            if telemetry_data.get(vector) is True:
                total_risk_incurred += weight
                logger.warning(
                    f"Fraud Risk Flagged: {vector} for User {user.id}. Adding {weight} points."
                )

        # 2. Historical Pattern Risk (Fake disputes, spam contracts)
        pattern_risk = PatternAnalyzer.evaluate_all_patterns(user)
        if pattern_risk > 0:
            total_risk_incurred += pattern_risk
            logger.warning(
                f"Historical Pattern Risk Flagged for User {user.id}. Adding {pattern_risk} points."
            )

        # 3. Clean Transaction Check
        if total_risk_incurred == 0:
            return profile, 0 

        # 4. Apply Risk and Check Thresholds
        profile.fraud_risk_score += total_risk_incurred
        
        # Silent Kill-Switch: If fraud score exceeds 100, lock the account instantly.
        if profile.fraud_risk_score >= 100:
            profile.status = GovernanceProfile.AccountStatus.SUSPENDED
            logger.critical(f"Account {user.id} SUSPENDED due to critical fraud risk.")
        # Optional: Add a RESTRICTED threshold here if you want it automated (e.g., >= 70)
        elif profile.fraud_risk_score >= 70:
            profile.status = GovernanceProfile.AccountStatus.RESTRICTED
            logger.warning(f"Account {user.id} RESTRICTED due to high fraud risk.")

        profile.save()

        # 5. Trigger Notifications on Status Change
        if initial_status != profile.status:
            if profile.status == profile.AccountStatus.SUSPENDED:
                Notification.objects.create(
                    user=user,
                    notification_type=Notification.NotificationType.SECURITY_ALERT,
                    title="Account Suspended",
                    message="Your account has been suspended due to detected security risks or abnormal activity. Please contact support."
                )
            elif profile.status == profile.AccountStatus.RESTRICTED:
                Notification.objects.create(
                    user=user,
                    notification_type=Notification.NotificationType.ACCOUNT_UPDATE,
                    title="Account Restricted",
                    message="Your account features have been temporarily restricted due to a low trust score or flagged activity."
                )

        return profile, total_risk_incurred