from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Transaction, CreditLog
from .serializers import TransactionSerializer, CreditLogSerializer
from .services import CreditService

class WalletBalanceView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        logs = CreditLog.objects.filter(user=request.user).order_by('-created_at')
        serializer = CreditLogSerializer(logs, many=True)
        return Response({
            "balance": request.user.wallet_balance,
            "logs": serializer.data
        })

class DepositView(generics.CreateAPIView):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        # In real app, interacting with Stripe/Razorpay happens here to get ID
        # For prototype, we just create a pending transaction
        serializer.save(user=self.request.user, type='DEPOSIT', status='PENDING')

class MockPaymentWebhookView(APIView):
    """
    Simulates a webhook from Stripe/Razorpay to confirm payment.
    """
    def post(self, request, transaction_id):
        # Secure this endpoint in production!
        success = CreditService.process_transaction(transaction_id)
        if success:
            return Response({"status": "Transaction Processed"})
        return Response({"status": "Failed"}, status=status.HTTP_400_BAD_REQUEST)
