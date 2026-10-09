from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from .email_utils import (
    send_account_activated_email,
    send_account_disabled_email,
    send_custom_user_email,
)
from .models import User
from .otp import qr_data_uri


class CustomUserMessageForm(forms.Form):
    subject = forms.CharField(
        label='Asunto',
        max_length=200,
        widget=forms.TextInput(attrs={'style': 'width:100%;box-sizing:border-box;'}),
    )
    message = forms.CharField(
        label='Mensaje',
        widget=forms.Textarea(attrs={'rows': 10, 'style': 'width:100%;box-sizing:border-box;'}),
        help_text='El mensaje se enviará por correo desde la dirección de notificaciones de la plataforma.',
    )


def _notify_status_change(user, new_status):
    if user.role == User.Role.ADMIN:
        return True, ''
    if new_status == User.Status.ACTIVE:
        return send_account_activated_email(user)
    if new_status == User.Status.DISABLED:
        return send_account_disabled_email(user)
    return True, ''


@admin.action(description='Habilitar usuarios seleccionados')
def activate_users(modeladmin, request, queryset):
    updated = 0
    failed = 0
    for user in queryset:
        if user.status == User.Status.ACTIVE:
            continue
        user.status = User.Status.ACTIVE
        user.save(update_fields=['status'])
        updated += 1
        ok, _ = send_account_activated_email(user)
        if not ok:
            failed += 1
    if updated:
        messages.success(request, f'{updated} usuario(s) habilitado(s).')
    if failed:
        messages.warning(request, f'{failed} correo(s) de habilitación no pudieron enviarse.')


@admin.action(description='Deshabilitar usuarios seleccionados')
def disable_users(modeladmin, request, queryset):
    updated = 0
    failed = 0
    for user in queryset:
        if user.status == User.Status.DISABLED:
            continue
        user.status = User.Status.DISABLED
        user.save(update_fields=['status'])
        updated += 1
        ok, _ = send_account_disabled_email(user)
        if not ok:
            failed += 1
    if updated:
        messages.success(request, f'{updated} usuario(s) deshabilitado(s).')
    if failed:
        messages.warning(request, f'{failed} correo(s) de deshabilitación no pudieron enviarse.')


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('name', 'email', 'role', 'status_badge', 'otp_badge', 'active_device_label', 'date_joined')
    list_filter = ('role', 'status', 'otp_enabled')
    search_fields = ('name', 'email')
    ordering = ('name', 'email')
    actions = [activate_users, disable_users]
    list_per_page = 25
    fieldsets = UserAdmin.fieldsets + (
        ('Aplicación', {'fields': ('name', 'role', 'status')}),
        ('Seguridad OTP', {'fields': ('otp_enabled', 'otp_qr_code', 'active_device_label', 'active_session_at'),
                           'description': 'Cada usuario creado tiene un QR OTP individual. Al editarlo puedes consultar el QR que debe registrarse en Google Authenticator, Microsoft Authenticator u otra aplicación TOTP.'}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos de la aplicación', {'fields': ('name', 'email', 'role', 'status')}),
    )
    readonly_fields = ('otp_qr_code', 'active_device_label', 'active_session_at')

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:user_id>/enviar-mensaje/',
                self.admin_site.admin_view(self.send_message_view),
                name='accounts_user_send_message',
            ),
        ]
        return custom + urls

    def send_message_view(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        if request.method == 'POST':
            form = CustomUserMessageForm(request.POST)
            if form.is_valid():
                ok, error = send_custom_user_email(
                    user,
                    form.cleaned_data['subject'],
                    form.cleaned_data['message'],
                )
                if ok:
                    messages.success(request, f'El mensaje fue enviado correctamente a {user.email}.')
                    return redirect(reverse('admin:accounts_user_change', args=[user.pk]))
                messages.error(request, f'No fue posible enviar el correo: {error}')
        else:
            form = CustomUserMessageForm()
        return render(request, 'admin/accounts/user/send_message.html', {
            **self.admin_site.each_context(request),
            'title': 'Enviar mensaje personalizado',
            'user': user,
            'form': form,
            'from_email': self._from_email(),
        })

    @staticmethod
    def _from_email():
        from django.conf import settings
        return settings.DEFAULT_FROM_EMAIL

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change and obj.pk:
            previous_status = User.objects.filter(pk=obj.pk).values_list('status', flat=True).first()
        super().save_model(request, obj, form, change)
        if change and previous_status != obj.status and obj.status in (User.Status.ACTIVE, User.Status.DISABLED):
            ok, error = _notify_status_change(obj, obj.status)
            if ok:
                messages.success(request, f'Se envió la notificación de estado a {obj.email}.')
            else:
                messages.warning(request, f'El estado se actualizó, pero no fue posible enviar la notificación a {obj.email}.')

    @admin.display(description='estado', ordering='status')
    def status_badge(self, obj):
        labels = {
            User.Status.ACTIVE: ('ACTIVO', 'status-active'),
            User.Status.PENDING: ('PENDIENTE DE PAGO', 'status-pending'),
            User.Status.DISABLED: ('DESHABILITADO', 'status-disabled'),
        }
        label, css = labels.get(obj.status, (obj.status, ''))
        return format_html('<span class="status-badge {}">{}</span>', css, label)

    @admin.display(description='OTP')
    def otp_badge(self, obj):
        if obj.otp_enabled:
            return format_html('<span class="status-badge status-active">ACTIVO</span>')
        return format_html('<span class="status-badge status-disabled">DESACTIVADO</span>')

    @admin.display(description='QR para Authenticator')
    def otp_qr_code(self, obj):
        if not obj.pk:
            return 'Guarda el usuario primero para generar su QR.'
        if not obj.otp_secret:
            return 'El secreto OTP aún no está disponible.'
        return format_html(
            '<div style="padding:12px;background:#fff;border:1px solid #ddd;border-radius:10px;display:inline-block;">'
            '<img src="{}" alt="Código QR OTP" style="width:220px;height:220px;display:block;">'
            '<p style="margin:10px 0 0;max-width:220px;font-size:12px;color:#667;">Escanea este QR con la aplicación Authenticator del usuario. Este código es individual y no debe compartirse.</p>'
            '</div>',
            qr_data_uri(obj),
        )


from django.contrib.auth.models import Group
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass
