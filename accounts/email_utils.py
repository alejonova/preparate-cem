import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _send(subject, recipient, template_name, context):
    if not recipient:
        return False, 'No se configuró un destinatario.'
    try:
        text_body = render_to_string(f'emails/{template_name}.txt', context).strip()
        html_body = render_to_string(f'emails/{template_name}.html', context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        message.attach_alternative(html_body, 'text/html')
        message.send(fail_silently=False)
        return True, ''
    except Exception as exc:
        logger.exception('No fue posible enviar correo a %s', recipient)
        return False, str(exc)


def send_account_created_email(user):
    return _send(
        'Tu cuenta fue creada satisfactoriamente — Preparate CEM - 2027',
        user.email,
        'account_created',
        {
            'user': user,
            'platform_name': 'Preparate CEM - 2027',
            'breb_key': settings.PAYMENT_BREB_KEY,
        },
    )


def send_account_activated_email(user):
    return _send(
        'Tu cuenta ha sido habilitada — Preparate CEM - 2027',
        user.email,
        'account_activated',
        {'user': user, 'platform_name': 'Preparate CEM - 2027'},
    )


def send_account_disabled_email(user):
    return _send(
        'Tu cuenta ha sido deshabilitada — Preparate CEM - 2027',
        user.email,
        'account_disabled',
        {'user': user, 'platform_name': 'Preparate CEM - 2027'},
    )


def send_new_user_admin_email(user):
    return _send(
        'Nuevo usuario registrado — Preparate CEM - 2027',
        settings.ADMIN_NOTIFICATION_EMAIL,
        'new_user_admin',
        {
            'user': user,
            'platform_name': 'Preparate CEM - 2027',
        },
    )


def send_custom_user_email(user, subject, message):
    try:
        html_body = render_to_string('emails/custom_message.html', {
            'user': user,
            'platform_name': 'Preparate CEM - 2027',
            'message_body': message,
        })
        text_body = render_to_string('emails/custom_message.txt', {
            'user': user,
            'platform_name': 'Preparate CEM - 2027',
            'message_body': message,
        }).strip()
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_body, 'text/html')
        email.send(fail_silently=False)
        return True, ''
    except Exception as exc:
        logger.exception('No fue posible enviar correo personalizado a %s', user.email)
        return False, str(exc)


def send_new_guide_email(user, guide):
    return _send(
        f'Nueva guía de estudio disponible — {guide.title}',
        user.email,
        'new_guide',
        {
            'user': user,
            'guide': guide,
            'platform_name': 'Preparate CEM - 2027',
        },
    )
