from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from accounts.views import login_view, logout_view, otp_verify, register, register_otp, my_account

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('login/otp/', otp_verify, name='otp_verify'),
    path('registro/', register, name='register'),
    path('registro/otp/', register_otp, name='register_otp'),
    path('mi-cuenta/', my_account, name='my_account'),
    path('', include('exams.urls')),
]
