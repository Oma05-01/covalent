from django.contrib import admin
from .models import CovalentUser, Wallet, Contract, Dispute, DisputeEvidence, ArbitrationVote, MerchantAPIKey
admin.site.register(CovalentUser)
admin.site.register(Wallet)
admin.site.register(Contract)
admin.site.register(Dispute)