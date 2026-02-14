from django.contrib.auth.models import AbstractUser
from django.db import models

from decimal import Decimal
import hashlib
import secrets

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


class AgentToken(models.Model):
    """Secure API token for GPU provider agents.
    
    The raw token is shown ONCE on creation and never stored.
    Only the SHA-256 hash is persisted (like a password).
    Tokens can be revoked from the dashboard.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agent_tokens')
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=100, default='Default Agent')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AgentToken({self.label}) for {self.user.username}"

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """SHA-256 hash a raw token string."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def generate(cls, user, label='Default Agent'):
        """Generate a new agent token. Returns (AgentToken, raw_token).
        
        The raw_token is returned ONCE and must be shown to the user immediately.
        It is NOT stored — only the hash is saved.
        """
        # Prefix with 'gpc_' for easy identification + 48 random bytes (hex)
        raw_token = f"gpc_{secrets.token_hex(32)}"
        token_hash = cls.hash_token(raw_token)
        agent_token = cls.objects.create(
            user=user,
            token_hash=token_hash,
            label=label,
        )
        return agent_token, raw_token

    @classmethod
    def validate(cls, raw_token: str):
        """Validate a raw token. Returns the AgentToken or None."""
        token_hash = cls.hash_token(raw_token)
        try:
            token = cls.objects.select_related('user').get(
                token_hash=token_hash,
                is_active=True
            )
            # Update last_used
            from django.utils import timezone
            token.last_used = timezone.now()
            token.save(update_fields=['last_used'])
            return token
        except cls.DoesNotExist:
            return None

