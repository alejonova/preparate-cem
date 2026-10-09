from django.contrib.auth import logout
from django.shortcuts import redirect
from .models import User


class NoCacheAuthenticatedMiddleware:
    """Evita que el navegador reutilice páginas autenticadas después del logout."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response


class PendingPaymentGateMiddleware:
    """Usuarios autenticados sin habilitación de pago solo pueden ver el portal cautivo."""

    ALLOWED_PREFIXES = (
        '/activar/', '/logout/', '/static/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.is_authenticated
            and not user.is_superuser
            and user.role != User.Role.ADMIN
            and user.status == User.Status.PENDING
            and not request.path.startswith(self.ALLOWED_PREFIXES)
        ):
            return redirect('activation_portal')
        return self.get_response(request)
