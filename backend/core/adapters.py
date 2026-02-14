from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import redirect
from django.conf import settings

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if hasattr(user, 'username') and not user.username:
            user.username = data.get('login') or data.get('email', '').split('@')[0] or "user"
        return user

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        """
        If OAuth fails, don't show the 'dirty' 8000 error page.
        Redirect back to the frontend login page with an error flag.
        """
        frontend_login_url = f"{settings.FRONTEND_URL}/login?error=oauth_failed"
        return redirect(frontend_login_url)
