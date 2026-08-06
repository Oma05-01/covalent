from django.test import TestCase
from django.contrib.auth import get_user_model
from governance.models import GovernanceProfile, TrustLog

User = get_user_model()

class GovernanceModelUnitTests(TestCase):
    
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword123"
        )
        # Create the associated governance profile
        self.profile = GovernanceProfile.objects.create(user=self.user)

    def test_default_values_are_correct(self):
        """Ensure a new profile starts with base trust and zero loyalty."""
        self.assertEqual(self.profile.trust_score, 50)
        self.assertEqual(self.profile.loyalty_points, 0)
        self.assertEqual(self.profile.fraud_risk_score, 0)
        self.assertEqual(self.profile.status, 'ACTIVE')

    def test_trust_score_never_exceeds_maximum_bound(self):
        """Even if 100 points are added, the score caps at 100."""
        self.profile.trust_score = 150 # Simulate a rogue calculation
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.trust_score, 100)

    def test_trust_score_never_drops_below_minimum_bound(self):
        """Repeated penalties hit a floor of 0 and don't go negative."""
        self.profile.trust_score = -20 # Simulate massive penalty
        self.profile.save()
        
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.trust_score, 0)

    def test_loyalty_points_accrue_correctly(self):
        """Loyalty points should accumulate normally without bounds."""
        self.profile.loyalty_points += 25
        self.profile.save()
        
        self.assertEqual(self.profile.loyalty_points, 25)
        
        self.profile.loyalty_points += 15
        self.profile.save()
        
        self.assertEqual(self.profile.loyalty_points, 40)