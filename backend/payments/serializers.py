from rest_framework import serializers
from .models import Transaction, CreditLog

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('status', 'user')

class CreditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditLog
        fields = '__all__'
