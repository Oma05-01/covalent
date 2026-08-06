import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

def get_client_ip(request):
    """Safely extracts the true client IP, even behind load balancers/proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can be a comma-separated list. The first is the real client.
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_velocity_spike(user_id, action="transaction", limit=5, timeout=60):
    """
    Tracks how many times a user performs an action within a timeframe.
    Returns True if they exceed the limit.
    """
    cache_key = f"velocity_{user_id}_{action}"
    
    try:
        # Atomic increment. Prevents race conditions in Redis/Memcached.
        current_count = cache.incr(cache_key)
    except ValueError:
        # If the key doesn't exist yet, cache.incr raises a ValueError in Django.
        cache.set(cache_key, 1, timeout=timeout)
        current_count = 1

    if current_count > limit:
        logger.warning(f"Velocity spike detected for user {user_id} on {action}.")
        return True
        
    return False

def check_failed_auth_burst(user_id, limit=3):
    """
    Checks if the user had multiple recent failed logins.
    Assumes your login view increments 'failed_auth_{user_id}' on bad passwords.
    """
    cache_key = f"failed_auth_{user_id}"
    attempts = cache.get(cache_key, 0)
    return attempts >= limit

def check_sim_swap(user):
    """
    Placeholder: Call external Telecom API (e.g., Dojah, Twilio Verify, Smile Identity).
    """
    # phone_number = getattr(user, 'phone_number', None)
    # if phone_number:
    #     response = requests.get(f"https://api.telecom.xyz/sim-status/{phone_number}")
    #     return response.json().get('swapped_recently', False)
    return False

def check_ip_mismatch(request, user):
    """
    Placeholder: Use GeoIP2 or IPinfo to verify IP country matches user's profile country.
    """
    # ip = get_client_ip(request)
    # request_country = get_country_from_ip(ip)
    # return request_country != user.profile.country
    return False

def gather_request_telemetry(request, user, action="transaction"):
    """
    Compiles the threat matrix dictionary for the RiskMitigationEngine.
    This is the single entry point called by your API Views.
    """
    payload = {
        'sim_swap_detected': check_sim_swap(user),
        'ip_geolocation_mismatch': check_ip_mismatch(request, user),
        'velocity_spike': check_velocity_spike(user.id, action=action),
        'failed_auth_burst': check_failed_auth_burst(user.id)
    }
    
    return payload