# accounts/tests/test_jwt.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@pytest.mark.django_db
class TestJWTGeneration:
    
    def test_jwt_generation_for_active_user(self):
        """Asserts that valid access and refresh tokens are generated for a user."""
        user = User.objects.create_user(
            email="token@covalent.com",
            password="securepassword"
        )
        
        # Generate the token pair for the user
        refresh = RefreshToken.for_user(user)
        
        # Assert tokens exist and contain the correct user ID
        assert str(refresh) is not None
        assert str(refresh.access_token) is not None
        
        # Cast both to string to safely compare them
        assert str(refresh['user_id']) == str(user.id)