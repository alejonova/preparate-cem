from django.contrib.auth.models import AbstractUser
from django.db import models
import pyotp


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        USER = 'USER', 'Usuario'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        ACTIVE = 'ACTIVE', 'Activo'
        DISABLED = 'DISABLED', 'Deshabilitado'

    name = models.CharField('nombre completo', max_length=150)
    email = models.EmailField('correo electrónico', unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    otp_secret = models.CharField('secreto OTP', max_length=32, blank=True, editable=False)
    otp_enabled = models.BooleanField('OTP habilitado', default=True)
    active_session_key = models.CharField('sesión activa', max_length=255, blank=True, editable=False)
    active_device_label = models.CharField('dispositivo con sesión activa', max_length=255, blank=True, editable=False)
    active_session_at = models.DateTimeField('inicio de sesión activo', null=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.otp_secret:
            self.otp_secret = pyotp.random_base32()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.username
