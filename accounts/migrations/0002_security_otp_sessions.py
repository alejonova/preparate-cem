from django.db import migrations, models


def populate_otp_secrets(apps, schema_editor):
    import pyotp
    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(otp_secret=''):
        user.otp_secret = pyotp.random_base32()
        user.save(update_fields=['otp_secret'])


class Migration(migrations.Migration):
    dependencies = [('accounts', '0001_initial')]
    operations = [
        migrations.AddField(model_name='user', name='otp_secret', field=models.CharField(blank=True, editable=False, max_length=32, verbose_name='secreto OTP')),
        migrations.AddField(model_name='user', name='otp_enabled', field=models.BooleanField(default=True, verbose_name='OTP habilitado')),
        migrations.AddField(model_name='user', name='active_session_key', field=models.CharField(blank=True, editable=False, max_length=255, verbose_name='sesión activa')),
        migrations.AddField(model_name='user', name='active_device_label', field=models.CharField(blank=True, editable=False, max_length=255, verbose_name='dispositivo con sesión activa')),
        migrations.AddField(model_name='user', name='active_session_at', field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name='inicio de sesión activo')),
        migrations.RunPython(populate_otp_secrets, migrations.RunPython.noop),
    ]
