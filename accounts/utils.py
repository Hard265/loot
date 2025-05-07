from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta

def get_password_reset_token_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["purpose"] = "password_reset"
    refresh.set_exp(lifetime=timedelta(minutes=5))

    return str(refresh.access_token)
