from .models import DeviceFingerprint, GovernanceProfile

class DeviceTracker:
    @staticmethod
    def extract_device_info(request):
        """Extracts IP and User-Agent from the DRF request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
            
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        return ip, user_agent

    @classmethod
    def process_and_check_evasion(cls, user, request) -> bool:
        """
        Records the user's device. 
        Returns True if this device is associated with a SUSPENDED account.
        """
        ip, user_agent = cls.extract_device_info(request)
        fingerprint_hash = DeviceFingerprint.generate_hash(ip, user_agent)

        # 1. Record/Update this user's footprint on this device
        DeviceFingerprint.objects.update_or_create(
            user=user,
            fingerprint_hash=fingerprint_hash,
            defaults={
                'ip_address': ip,
                'user_agent': user_agent
            }
        )

        # 2. Ban Evasion Check: Are there any OTHER users on this exact device who are suspended?
        toxic_devices = DeviceFingerprint.objects.filter(
            fingerprint_hash=fingerprint_hash
        ).exclude(user=user) # Exclude the current user

        for device in toxic_devices:
            if device.user.governance_profile.status == GovernanceProfile.AccountStatus.SUSPENDED:
                return True  # Ban evasion detected!
                
        return False