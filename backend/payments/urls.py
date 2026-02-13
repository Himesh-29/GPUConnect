from django.urls import path
from .views import WalletBalanceView, DepositView, MockPaymentWebhookView

urlpatterns = [
    path('wallet/', WalletBalanceView.as_view(), name='wallet'),
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('webhook/mock/<int:transaction_id>/', MockPaymentWebhookView.as_view(), name='mock-webhook'),
]
