from rest_framework.views import APIView
from rest_framework.response import Response
from .models import MerchantAPIKey, Contract
from .serializers import ContractSerializer

class ExternalCheckoutView(APIView):
    def post(self, request):
        # 1. Validate API Key
        key = request.headers.get("X-Covalent-API-Key")
        api_key = MerchantAPIKey.objects.filter(key=key).first()
        if not api_key:
            return Response({"detail": "Invalid or missing API Key."}, status=403)

        # 2. Map external store data to our Contract Model
        data = request.data
        contract = Contract.objects.create(
            creator=api_key.user,
            vendor_email=data.get("vendor_email"),
            item_title=data.get("item_name"),
            item_description=data.get("description"),
            item_amount=data.get("price"),
            delivery_fee=data.get("shipping_fee"),
            plain_language_summary=data.get("description"),
        )
        
        # 3. Return a secure checkout link
        return Response({
            "escrow_link": f"http://localhost:5173/checkout/{contract.contract_id}",
            "contract_id": str(contract.contract_id)
        }, status=201)