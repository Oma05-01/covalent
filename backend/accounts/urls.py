from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    ContractDeleteView, DevKeysView, KYCVerificationView, RegistrationView, UserProfileView, BankListView, 
    ResolveAccountView, LinkBankView, WalletDashboardView,
    paystack_webhook,
     PlatformAdminDashboardView, AdminUserManagementView,
)

urlpatterns = [
    # Auth & Profile
    path('auth/register/', RegistrationView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('kyc/verify/', KYCVerificationView.as_view(), name='kyc_verify'),
    
    # Phase 2: Paystack Wallet & Bank Setup
    path('banks/', BankListView.as_view(), name='bank_list'),
    path('wallet/resolve/', ResolveAccountView.as_view(), name='resolve_account'),
    path('wallet/link/', LinkBankView.as_view(), name='link_bank'),
    path('wallet/', WalletDashboardView.as_view(), name='wallet_dashboard'),

    # Phase 3 & 4: Contracts, Payments, Webhook & Fulfillment
    path('webhook/paystack/', paystack_webhook, name='paystack_webhook'),
    path('contracts/<uuid:contract_id>/delete/', ContractDeleteView.as_view(), name='contract-delete'),

    
    # Phase 7: Admin & Revenue Command Center
    path('admin/analytics/', PlatformAdminDashboardView.as_view(), name='admin_analytics'),
    path('admin/users/', AdminUserManagementView.as_view(), name='admin_users'),
    path('admin/users/action/', AdminUserManagementView.as_view(), name='admin_user_action'),

    path('dev/keys/', DevKeysView.as_view(), name='dev_keys'),



]