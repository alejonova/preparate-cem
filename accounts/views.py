from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.sessions.models import Session
from django.shortcuts import redirect, render
from django.utils import timezone
from django.conf import settings
import pyotp

from .email_utils import send_account_created_email, send_new_user_admin_email

from .models import User
from .otp import qr_data_uri_for_secret


def _device_label(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    if 'Edg/' in ua:
        browser = 'Edge'
    elif 'Chrome/' in ua:
        browser = 'Chrome'
    elif 'Firefox/' in ua:
        browser = 'Firefox'
    elif 'Safari/' in ua:
        browser = 'Safari'
    else:
        browser = 'Navegador'
    if 'Windows' in ua:
        os_name = 'Windows'
    elif 'Mac OS X' in ua or 'Macintosh' in ua:
        os_name = 'macOS'
    elif 'Android' in ua:
        os_name = 'Android'
    elif 'iPhone' in ua or 'iPad' in ua:
        os_name = 'iOS'
    elif 'Linux' in ua:
        os_name = 'Linux'
    else:
        os_name = 'dispositivo desconocido'
    return f'{browser} en {os_name}'


def _clear_registration_session(request):
    for key in (
        'registration_email', 'registration_name', 'registration_password_hash',
        'registration_otp_secret'
    ):
        request.session.pop(key, None)
    request.session.modified = True


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        if not name or not email or not password:
            messages.error(request, 'Todos los campos son obligatorios.')
        elif password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario registrado con ese correo.')
        elif len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            secret = pyotp.random_base32()
            request.session['registration_email'] = email
            request.session['registration_name'] = name
            request.session['registration_password_hash'] = make_password(password)
            request.session['registration_otp_secret'] = secret
            request.session.modified = True
            return redirect('register_otp')
    return render(request, 'registration/register.html')


def register_otp(request):
    email = request.session.get('registration_email')
    name = request.session.get('registration_name')
    secret = request.session.get('registration_otp_secret')
    password_hash = request.session.get('registration_password_hash')
    if not all((email, name, secret, password_hash)):
        return redirect('register')

    if request.method == 'POST':
        code = request.POST.get('otp_code', '').strip().replace(' ', '')
        if len(code) == 6 and pyotp.TOTP(secret).verify(code, valid_window=1):
            if User.objects.filter(email=email).exists():
                _clear_registration_session(request)
                messages.error(request, 'Ese correo ya tiene una cuenta registrada. Puedes iniciar sesión.')
                return redirect('login')
            user = User(
                username=email,
                email=email,
                name=name,
                status=User.Status.PENDING,
                role=User.Role.USER,
                otp_secret=secret,
                otp_enabled=True,
            )
            user.password = password_hash
            user.save()
            _clear_registration_session(request)
            _activate_session_for_user(request, user, previous_key='', previous_device='')

            created_ok, created_error = send_account_created_email(user)
            admin_ok, admin_error = send_new_user_admin_email(user)
            if not created_ok or not admin_ok:
                messages.warning(request, 'La cuenta fue creada correctamente, pero uno de los correos de notificación no pudo enviarse. El administrador puede revisar la configuración del correo.')
            messages.success(request, '¡Bienvenido a Preparate CEM - 2027! Tu cuenta fue creada y quedó pendiente de habilitación por pago.')
            return redirect('home')
        messages.error(request, 'El código OTP no es válido o ya expiró. Verifica la aplicación Authenticator e inténtalo nuevamente.')

    return render(request, 'registration/register_otp.html', {
        'email': email,
        'name': name,
        'qr_data': qr_data_uri_for_secret(email, secret),
        'otp_secret': secret,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user.status == User.Status.DISABLED:
            form.add_error(None, 'Esta cuenta está deshabilitada.')
        else:
            device = _device_label(request)
            previous_key = user.active_session_key
            previous_device = user.active_device_label or 'otro dispositivo'
            request.session.flush()
            request.session['pending_otp_user_id'] = user.pk
            request.session['pending_otp_device'] = device
            request.session['pending_otp_previous_key'] = previous_key or ''
            request.session['pending_otp_previous_device'] = previous_device if previous_key else ''
            request.session.modified = True
            if not user.otp_enabled:
                _finish_login_after_otp(request, user)
                return redirect('home')
            return redirect('otp_verify')
    return render(request, 'registration/login.html', {'form': form})


def _activate_session_for_user(request, user, previous_key='', previous_device=''):
    if previous_key and previous_key != request.session.session_key:
        Session.objects.filter(session_key=previous_key).delete()
    login(request, user)
    device = request.session.get('pending_otp_device', _device_label(request))
    user.active_session_key = request.session.session_key
    user.active_device_label = device
    user.active_session_at = timezone.now()
    user.save(update_fields=['active_session_key', 'active_device_label', 'active_session_at'])
    if previous_key:
        messages.warning(request, f'Se cerró automáticamente la sesión anterior abierta en el dispositivo «{previous_device or "otro dispositivo"}».')


def _finish_login_after_otp(request, user):
    previous_key = request.session.get('pending_otp_previous_key', '')
    previous_device = request.session.get('pending_otp_previous_device', '')
    _activate_session_for_user(request, user, previous_key, previous_device)
    for key in ('pending_otp_user_id', 'pending_otp_device', 'pending_otp_previous_key', 'pending_otp_previous_device'):
        request.session.pop(key, None)
    request.session.modified = True


def otp_verify(request):
    user_id = request.session.get('pending_otp_user_id')
    if not user_id:
        return redirect('login')
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('login')

    if request.method == 'POST':
        code = request.POST.get('otp_code', '').strip().replace(' ', '')
        if (not user.otp_enabled) or (len(code) == 6 and pyotp.TOTP(user.otp_secret).verify(code, valid_window=1)):
            _finish_login_after_otp(request, user)
            return redirect('home')
        messages.error(request, 'El código OTP no es válido o ya expiró.')
    return render(request, 'registration/otp_verify.html', {'user': user})


def my_account(request):
    if not request.user.is_authenticated:
        return redirect('login')
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'profile':
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            current_password = request.POST.get('current_password', '')

            if not name or not email:
                messages.error(request, 'El nombre y el correo electrónico son obligatorios.')
            elif email != user.email and not user.check_password(current_password):
                messages.error(request, 'Para cambiar el correo electrónico debes confirmar tu contraseña actual.')
            elif email != user.email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
                messages.error(request, 'Ya existe otra cuenta registrada con ese correo electrónico.')
            else:
                changed_fields = []
                if user.name != name:
                    user.name = name
                    changed_fields.append('name')
                if user.email != email:
                    user.email = email
                    user.username = email
                    changed_fields.extend(['email', 'username'])
                if changed_fields:
                    user.save(update_fields=changed_fields)
                    messages.success(request, 'Tus datos personales fueron actualizados correctamente.')
                else:
                    messages.info(request, 'No había cambios para guardar.')
            return redirect('my_account')

        if action == 'password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            new_password2 = request.POST.get('new_password2', '')

            if not user.check_password(current_password):
                messages.error(request, 'La contraseña actual no es correcta.')
            elif not new_password:
                messages.error(request, 'Debes indicar una nueva contraseña.')
            elif new_password != new_password2:
                messages.error(request, 'Las nuevas contraseñas no coinciden.')
            else:
                try:
                    validate_password(new_password, user=user)
                except ValidationError as exc:
                    for error in exc.messages:
                        messages.error(request, error)
                else:
                    user.set_password(new_password)
                    user.save(update_fields=['password'])
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Tu contraseña fue cambiada correctamente.')
            return redirect('my_account')

    return render(request, 'registration/my_account.html', {
        'account_user': user,
        'otp_qr': qr_data_uri_for_secret(user.email, user.otp_secret),
        'otp_secret': user.otp_secret,
    })


def logout_view(request):
    user = request.user
    if user.is_authenticated and user.active_session_key == request.session.session_key:
        user.active_session_key = ''
        user.active_device_label = ''
        user.active_session_at = None
        user.save(update_fields=['active_session_key', 'active_device_label', 'active_session_at'])
    logout(request)
    return redirect('login')
