from django.contrib.auth.models import AbstractUser
from django.db import models

from decimal import Decimal

class User(AbstractUser):
    # Role choices
    ROLE_CHOICES = (
        ('USER', 'User'),
        ('PROVIDER', 'GPU Provider'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='USER')
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100.00'))
    
    def __str__(self):
        return self.username
