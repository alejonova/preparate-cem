# Aplicación de práctica de exámenes

Django + SQLite + Docker para práctica privada de exámenes.

## Incluye
- Cinco bancos de 100 preguntas.
- Exámenes aleatorios de 40 preguntas y 80 minutos.
- Opciones A/B/C/D aleatorizadas por examen.
- Resultados e historial por materia.
- Registro en dos pasos con configuración y confirmación OTP.
- Usuario nuevo queda PENDING (pendiente de pago) hasta habilitación administrativa.
- Portal cautivo de pago para usuarios PENDING.
- Administración rediseñada.
- Biblioteca independiente de guías PDF, almacenadas en `data/guias/` y servidas mediante Django sin exponer esa carpeta.
- Control de una sola sesión activa por usuario: al iniciar sesión correctamente en otro dispositivo, se invalida la sesión anterior y se informa el dispositivo.
- Autenticación TOTP/OTP de seis dígitos mediante aplicaciones Authenticator. Cada usuario tiene un secreto independiente.
- Nueva sección **Mi Cuenta** para que el usuario pueda actualizar nombre, cambiar correo electrónico con confirmación de contraseña actual, cambiar contraseña y recuperar el QR y la clave manual del mismo OTP ya configurado.
- El QR y la clave OTP de **Mi Cuenta no regeneran ni modifican** el secreto existente.
- Número de la llave Bre-B resaltado y separado visualmente en el portal de pago.

## Datos persistentes
El volumen `./data:/app/data` conserva SQLite, bancos y guías PDF.

## Mi Cuenta
La ruta `/mi-cuenta/` requiere autenticación y queda integrada en la navegación principal para usuarios con acceso a la plataforma. El cambio de correo exige verificar la contraseña actual; además se valida que el nuevo correo no pertenezca a otra cuenta. El cambio de contraseña conserva la sesión activa actual. El QR y la clave manual se generan a partir del secreto OTP existente del usuario, sin crear uno nuevo.

## Guías
El administrador puede entrar en **Guías de estudio** dentro de Django Admin y subir archivos PDF asociados a una materia. Los archivos quedan físicamente bajo `/app/data/guias/` dentro del contenedor y no se publican mediante una URL de medios; la descarga pasa por una vista autenticada de Django.

## OTP
Al crear un usuario se genera automáticamente un secreto TOTP individual. Al guardar el usuario, su ficha administrativa muestra un QR para registrarlo en Google Authenticator, Microsoft Authenticator u otra aplicación compatible. El acceso normal requiere contraseña y el código OTP, salvo que el administrador desactive explícitamente OTP para una cuenta.

## Sesiones
Solo se mantiene una sesión activa por cuenta en el acceso normal. El segundo inicio de sesión no invalida la sesión anterior hasta que el nuevo acceso supere la verificación OTP. Al completarla, se elimina la sesión anterior y se muestra el dispositivo que fue cerrado.

## Docker
```bash
docker compose up -d --build
```

El entrypoint ejecuta migraciones, importa los bancos y recopila estáticos al arrancar.

## Versión 1.4 - progreso, registro OTP y portada pública

Cambios:
- Corregida la gráfica de barras de mejor puntaje por materia: se añadieron los estilos de `.progress-list`, `.progress-row`, `.progress-track`, `.progress-bar` y recomendación.
- Durante el registro OTP se muestra debajo del QR la clave de configuración manual para quienes no puedan escanearlo.
- La clave mostrada durante el registro corresponde al mismo secreto OTP que se guarda al confirmar la cuenta; no se genera una segunda clave.
- La pantalla pública de inicio de sesión fue rediseñada como portada de bienvenida, con explicación de Test Simulacro, Guías, progreso y llamadas a crear cuenta.
- No se modifican la base de datos, los secretos OTP existentes, las guías ni el archivo `.env`.

## Correo de notificaciones por Apple Brevo SMTP

La plataforma puede enviar notificaciones mediante el SMTP de Apple/iCloud usando la cuenta `notificaciones@cem2027.lat`.
La contraseña específica de aplicación debe configurarse únicamente en el archivo `.env` del NAS y nunca debe publicarse en GitHub.

Variables requeridas en `.env`:

- `EMAIL_HOST=smtp-relay.brevo.com`
- `EMAIL_PORT=587`
- `EMAIL_USE_TLS=True`
- `EMAIL_USE_SSL=False`
- `EMAIL_HOST_USER`: login SMTP que entrega Brevo en la sección SMTP & API.
- `EMAIL_HOST_PASSWORD`: clave SMTP generada en Brevo; no es la clave API.
- `EMAIL_TIMEOUT=20`
- `DEFAULT_FROM_EMAIL=Preparate CEM - 2027 <notificaciones@cem2027.lat>`
- `ADMIN_NOTIFICATION_EMAIL=admin@cem2027.lat`
- `PAYMENT_BREB_KEY=3103358089`

**Seguridad:** no copies el `.env` real dentro del ZIP ni compartas credenciales por chat. Modifica el `.env` existente directamente en el NAS. Mantén las credenciales fuera del repositorio y conserva el resto de sus variables actuales.

Notificaciones implementadas:
- creación de cuenta: correo al usuario con instrucciones de pago y aviso al administrador;
- habilitación de cuenta;
- deshabilitación de cuenta;
- nueva guía de estudio activa: aviso a usuarios activos;
- mensaje personalizado desde el panel de administración a un usuario específico.

No se implementan recordatorios automáticos por inactividad ni se almacenan correos enviados en SQLite.
