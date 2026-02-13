from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', include('core.urls')),
    path('api/computing/', include('computing.urls')),
    path('api/payments/', include('payments.urls')),
]
