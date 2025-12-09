# auth/api/urls.py

from django.urls import path
from .views import ActivateView
from .views import RegisterView

app_name = "auth_api"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("activate/<uidb64>/<token>/", ActivateView.as_view(), name="activate"),
]
