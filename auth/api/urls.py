# auth/api/urls.py

from django.urls import path
from .views import ActivateView, RegisterView, LoginView
from django.urls import path
from .views import ActivateView, RegisterView, LoginView, LogoutView


app_name = "auth_api"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activate/<uidb64>/<token>/", ActivateView.as_view(), name="activate"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]