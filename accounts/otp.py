import base64
from io import BytesIO

import pyotp
import qrcode


def provisioning_uri_for_secret(email, secret):
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name='Preparate CEM - 2027')


def provisioning_uri(user):
    return provisioning_uri_for_secret(user.email, user.otp_secret)


def qr_data_uri_for_secret(email, secret):
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(provisioning_uri_for_secret(email, secret))
    qr.make(fit=True)
    image = qr.make_image()
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def qr_data_uri(user):
    return qr_data_uri_for_secret(user.email, user.otp_secret)
