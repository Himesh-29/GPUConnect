from django.db import transaction
from .models import CreditLog, Transaction
from django.contrib.auth import get_user_model

User = get_user_model()

class CreditService:
    @staticmethod
    @transaction.atomic
    def process_transaction(transaction_id):
        """
        Finalizes a pending transaction and updates user wallet.
        """
        try:
            txn = Transaction.objects.select_for_update().get(id=transaction_id)
            if txn.status != 'PENDING':
                return False
            
            user = txn.user
            if txn.type == 'DEPOSIT':
                user.wallet_balance += txn.amount
                CreditLog.objects.create(
                    user=user,
                    amount=txn.amount,
                    description=f"Deposit via {txn.gateway_id}"
                )
                txn.status = 'SUCCESS'
            elif txn.type == 'WITHDRAWAL':
                if user.wallet_balance < txn.amount:
                    txn.status = 'FAILED'
                    txn.save()
                    return False
                
                user.wallet_balance -= txn.amount
                CreditLog.objects.create(
                    user=user,
                    amount=-txn.amount,
                    description=f"Withdrawal request"
                )
                txn.status = 'SUCCESS' # Or PENDING_APPROVAL
            
            txn.save()
            user.save()
            return True
        except Transaction.DoesNotExist:
            return False

    @staticmethod
    @transaction.atomic
    def transfer_credits(sender, receiver, amount, job_id=None):
        """
        Transfers credits from Consumer (sender) to Provider (receiver).
        """
        if sender.wallet_balance < amount:
            raise ValueError("Insufficient funds")
        
        sender.wallet_balance -= amount
        sender.save()
        CreditLog.objects.create(user=sender, amount=-amount, description=f"Payment for Job {job_id}")

        receiver.wallet_balance += amount
        receiver.save()
        CreditLog.objects.create(user=receiver, amount=amount, description=f"Earnings for Job {job_id}")
