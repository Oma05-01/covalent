from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/escrow/', include('escrow.urls')),
    path('api/v1/governance/', include('governance.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/audit/', include('audit.urls')),
]