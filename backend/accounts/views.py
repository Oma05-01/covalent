from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Sum, Avg
import requests
import hmac
import hashlib
import requests
from decimal import Decimal

from .models import Wallet, Contract, CovalentUser, Dispute, DisputeEvidence, ArbitrationVote, MerchantAPIKey, PlatformAuditLog
from .serializers import (
    KYCSubmissionSerializer, UserProfileSerializer, WalletSerializer, 
    BankResolveSerializer, BankLinkSerializer, RegistrationSerializer, ContractSerializer
)
from .paystack import PaystackService


class KYCVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        
        if user.is_kyc_verified:
            return Response(
                {"detail": "Your account is already KYC verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = KYCSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nin = str(serializer.validated_data["nin"])
        
        user.nin = nin
        user.is_kyc_verified = True
        user.trust_score = min(user.trust_score + 5, 100)
        user.save()

        return Response({
            "message": "KYC verification successful!",
            "user": UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens for the immediate login
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": serializer.data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class BankListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        service = PaystackService()
        banks = service.get_nigerian_banks()
        bank_list = [{"name": b["name"], "code": b["code"]} for b in banks]
        return Response(bank_list, status=status.HTTP_200_OK)


class ResolveAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        serializer = BankResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = PaystackService()
        data = service.resolve_account_number(
            serializer.validated_data['account_number'],
            serializer.validated_data['bank_code']
        )
        return Response(data, status=status.HTTP_200_OK)


class LinkBankView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        user = request.user
        serializer = BankLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        bank_code = serializer.validated_data['bank_code']
        account_number = serializer.validated_data['account_number']
        account_name = serializer.validated_data['account_name']
        bank_name = serializer.validated_data['bank_name']

        service = PaystackService()
        subaccount_code = service.create_subaccount(user, bank_code, account_number, account_name)

        user.paystack_subaccount_code = subaccount_code
        user.bank_name = bank_name
        user.account_number = account_number
        user.account_name = account_name
        user.save()

        Wallet.objects.get_or_create(user=user)

        return Response({
            "message": "Bank account linked successfully for split payouts!",
            "subaccount_code": subaccount_code
        }, status=status.HTTP_200_OK)


class WalletDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response({
            "wallet": WalletSerializer(wallet).data,
            "bank_info": {
                "bank_name": request.user.bank_name,
                "account_number": request.user.account_number,
                "account_name": request.user.account_name,
                "is_linked": bool(request.user.paystack_subaccount_code)
            }
        }, status=status.HTTP_200_OK)
    



@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """Secure background listener for Paystack payment notifications."""
    paystack_signature = request.headers.get('x-paystack-signature')
    if not paystack_signature:
        return Response({"detail": "Missing Paystack signature header."}, status=status.HTTP_400_BAD_REQUEST)

    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        request.body,
        hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, paystack_signature):
        return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data
    event = payload.get('event')
    data = payload.get('data', {})

    if event == 'charge.success':
        reference = data.get('reference')
        try:
            contract = Contract.objects.get(paystack_reference=reference, status="AWAITING_FUNDING")
            contract.status = "FUNDED"
            contract.save()
            
            vendor_wallet, _ = Wallet.objects.get_or_create(user__email=contract.vendor_email)
            vendor_wallet.locked_escrow_balance += contract.total_escrow
            vendor_wallet.save()
            
        except Contract.DoesNotExist:
            pass

    return Response(status=status.HTTP_200_OK)


class ContractDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, contract_id):
        try:
            contract = Contract.objects.get(
                contract_id=contract_id,
                creator=request.user,
                status__in=["DRAFT", "AWAITING_FUNDING", "UNFUNDED"]
            )
            contract.delete()
            return Response({"message": "Draft contract deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Contract.DoesNotExist:
            return Response(
                {"detail": "Draft not found or cannot be deleted once funded or disputed."},
                status=status.HTTP_400_BAD_REQUEST
            )
    

class PlatformAdminDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied. Admin privileges required."}, status=403)

        # 1. Financial Metrics Aggregation
        released_contracts = Contract.objects.filter(status="RELEASED")
        total_gmv = released_contracts.aggregate(total=Sum('total_escrow'))['total'] or Decimal('0.00')
        
        # Covalent takes 5% of all released escrow deals
        platform_revenue = total_gmv * Decimal('0.05')
        
        # Money currently sitting locked inside active deals
        locked_vault = Wallet.objects.aggregate(total=Sum('locked_escrow_balance'))['total'] or Decimal('0.00')
        
        # 2. System Health & Governance Metrics
        active_disputes = Dispute.objects.filter(status="IN_REVIEW").count()
        avg_trust_score = CovalentUser.objects.aggregate(avg=Avg('trust_score'))['avg'] or 0
        total_users = CovalentUser.objects.count()
        verified_lawyers = CovalentUser.objects.filter(is_lawyer=True).count()

        return Response({
            "financials": {
                "total_gmv": total_gmv,
                "platform_revenue": platform_revenue,
                "locked_vault": locked_vault,
            },
            "governance": {
                "active_disputes": active_disputes,
                "avg_trust_score": round(avg_trust_score, 1),
                "total_users": total_users,
                "verified_lawyers": verified_lawyers,
            }
        }, status=status.HTTP_200_OK)


class AdminUserManagementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied."}, status=403)
            
        users = CovalentUser.objects.all().order_by('-date_joined')[:20]
        data = []
        for u in users:
            # Safely get the wallet balance
            balance = 0
            try:
                # This now works because of the related_name="wallet" fix
                balance = u.wallet.available_balance 
            except AttributeError:
                balance = 0
                
            data.append({
                "id": u.id,
                "email": u.email,
                "name": f"{u.first_name} {u.last_name}",
                "trust_score": u.trust_score,
                "is_kyc_verified": u.is_kyc_verified,
                "is_lawyer": u.is_lawyer,
                "is_active": u.is_active,
                "wallet_balance": balance,
            })
        return Response(data, status=200)

    def patch(self, request, user_id):
        if not (request.user.is_superuser or request.user.is_staff):
            return Response({"detail": "Access denied."}, status=403)
            
        try:
            target_user = CovalentUser.objects.get(id=user_id)
        except CovalentUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        action = request.data.get("action")
        
        if action == "toggle_lawyer":
            target_user.is_lawyer = not target_user.is_lawyer
            target_user.save()
            return Response({"message": f"Lawyer status set to {target_user.is_lawyer}"})
            
        elif action == "boost_trust":
            target_user.trust_score = min(target_user.trust_score + 10, 100)
            target_user.save()
            return Response({"message": f"Trust score boosted to {target_user.trust_score}"})
            
        elif action == "penalize_trust":
            target_user.trust_score = max(target_user.trust_score - 15, 0)
            target_user.save()
            return Response({"message": f"Trust score penalized to {target_user.trust_score}"})

        return Response({"detail": "Invalid action."}, status=400)
    
def trigger_merchant_webhook(contract, event_type):
    # This logic would be called by your Celery worker 
    # when contract.status changes
    payload = {
        "event": event_type,
        "contract_id": str(contract.contract_id),
        "status": contract.status
    }
    # In a real app, you'd store the merchant's webhook_url in MerchantAPIKey
    # requests.post("https://merchant-store.com/webhooks/covalent", json=payload)
    print(f"Webhook {event_type} sent for {contract.contract_id}")


class DevKeysView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        keys = MerchantAPIKey.objects.filter(user=request.user)
        return Response([{'id': k.id, 'name': k.name, 'key': k.key} for k in keys])

    def post(self, request):
        key = MerchantAPIKey.objects.create(user=request.user, name=request.data.get('name'))
        return Response({'id': key.id, 'name': key.name, 'key': key.key})